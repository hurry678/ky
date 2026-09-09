"""
假设 5 附带发现：mem0 delete() 的存储层明文残留
用 mem0 真实 SQLiteManager，按 mem0/memory/main.py 的实际调用序列复现。
参考行号（mem0 main 分支 2026-09-08）：
  L1082  add_history(memory_id, None, new_memory, "ADD", ...)
  L2112  add_history(memory_id, prev_value, None, "DELETE", ..., is_deleted=1)
  L2114 前 vector_store.delete(vector_id=memory_id)
"""
import importlib.util, pathlib, sqlite3, uuid, os
from datetime import datetime, timezone

SRC = pathlib.Path("mem0_src/mem0/memory/storage.py")
spec = importlib.util.spec_from_file_location("m0storage", SRC)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

DB = "mem0_leak_demo.sqlite"
if os.path.exists(DB): os.remove(DB)
db = m.SQLiteManager(db_path=DB)

# 一条带 PII 的记忆，模拟用户后来行使删除权
SECRET = "User's HIV test came back positive on 2026-03-14; partner not yet informed."
mid = str(uuid.uuid4())
now = datetime.now(timezone.utc).isoformat()

# --- 阶段 1：写入（main.py L1082 的调用形式）---
db.add_history(mid, None, SECRET, "ADD", created_at=now)

# --- 阶段 2：用户请求删除（main.py L2100-2123 的调用形式）---
# 真实代码此处先 self.vector_store.delete(vector_id=memory_id) —— 向量确实删了
db.add_history(mid, SECRET, None, "DELETE",
               created_at=now, updated_at=now, is_deleted=1)

# --- 阶段 3：站在攻击者/内部人员角度直接读库 ---
con = sqlite3.connect(DB)
rows = con.execute(
    "SELECT event, old_memory, new_memory, is_deleted FROM history WHERE memory_id=?",
    (mid,)).fetchall()

print(f"删除后 history 表中该 memory_id 的记录数: {len(rows)}")
hits = 0
for ev, old, new, dele in rows:
    for col, val in (("old_memory", old), ("new_memory", new)):
        if val and SECRET in val:
            hits += 1
            print(f"  [{ev:6s} is_deleted={dele}] {col} = {val!r}")
print(f"\n删除后仍可从 SQLite 恢复的明文副本数: {hits}")

# 全表扫描：不带 memory_id 过滤，模拟拖库
n = con.execute("SELECT COUNT(*) FROM history WHERE old_memory LIKE ? OR new_memory LIKE ?",
                ("%HIV%", "%HIV%")).fetchone()[0]
print(f"全表 LIKE '%HIV%' 命中行数: {n}")
print(f"\n结论: vector_store 已删除该条向量，但明文在 {DB} 中留存 {hits} 份，"
      f"is_deleted=1 仅为标记位，无加密、无覆写。")
con.close()
