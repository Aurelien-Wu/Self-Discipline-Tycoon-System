# -*- coding: utf-8 -*-
import csv
import json
import os
import random
import sqlite3
import tempfile
import uuid
from datetime import date, datetime, time, timedelta


# ============ 配置 ============
COMMISSION_RATE = 0.01
DAILY_REWARD_CAP = 30.0
COMMISSION_STOP_N = 100
REWARD_TIERS = [0.25, 0.5, 0.75, 1.0]
REWARD_MIN = 3.0
REWARD_MAX = 10.0
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

SCHEMA =""
"CREATE TABLE IF NOT EXISTS users ("
"    user_id TEXT PRIMARY KEY,"
"    balance REAL DEFAULT 0,"
"    total_reward REAL DEFAULT 0,"
"    total_recharge REAL DEFAULT 0,"
"    total_commission REAL DEFAULT 0,"
"    completed_tasks INTEGER DEFAULT 0,"
"    streak INTEGER DEFAULT 0,"
"    last_complete_date TEXT,"
"    commission_stopped INTEGER DEFAULT 0,"
"    created_at TEXT"
");"
"CREATE TABLE IF NOT EXISTS study_tasks ("
"    task_id TEXT PRIMARY KEY,"
"    user_id TEXT,"
"    date TEXT,"
"    start TEXT,"
"    end TEXT,"
"    course TEXT,"
"    difficulty INTEGER,"
"    duration_min INTEGER,"
"    reward REAL,"
"    status TEXT DEFAULT 'pending',"
"    completed_at TEXT"
");"
"CREATE TABLE IF NOT EXISTS entertainment_tasks ("
"    task_id TEXT PRIMARY KEY,"
"    user_id TEXT,"
"    line TEXT,"
"    action TEXT,"
"    target TEXT,"
"    status TEXT DEFAULT 'pending',"
"    drawn_at TEXT,"
"    completed_at TEXT"
");"
"CREATE TABLE IF NOT EXISTS recharges ("
"    id INTEGER PRIMARY KEY AUTOINCREMENT,"
"    user_id TEXT,"
"    amount REAL,"
"    commission REAL,"
"    net REAL,"
"    created_at TEXT"
");"
"CREATE TABLE IF NOT EXISTS achievements ("
"    id INTEGER PRIMARY KEY AUTOINCREMENT,"
"    user_id TEXT,"
"    achievement_id TEXT,"
"    name TEXT,"
"    type TEXT,"
"    unlocked_at TEXT,"
"    UNIQUE(user_id, achievement_id)"
");"
"CREATE TABLE IF NOT EXISTS daily_stats ("
"    user_id TEXT,"
"    date TEXT,"
"    completed_ratio REAL,"
"    reward REAL,"
"    study_minutes INTEGER,"
"    PRIMARY KEY (user_id, date)"
");"


DEFAULT_SCHEDULE = """course,day,start,end,difficulty,credits,assignment_due,exam_date
Math,Mon,08:00,09:40,5,4,2026-10-10,2026-11-01
Physics,Mon,10:00,11:40,4,3,,2026-11-05
English,Tue,09:00,10:30,3,2,2026-10-15,
Data Structure,Tue,14:00,15:40,5,4,2026-10-08,2026-11-10
Math,Wed,08:00,09:40,5,4,,
Physics,Wed,14:00,15:40,4,3,,2026-11-05
English,Thu,10:00,11:30,3,2,,
Data Structure,Thu,15:00,16:40,5,4,,2026-11-10
Math,Fri,08:00,09:40,5,4,,
English,Fri,13:00,14:30,3,2,2026-10-20,
"""

LINES = [
    "愚蠢的人类啊，臣服吧。",
    "我乃新世界的神！",
    "感受痛苦吧，思考痛苦吧，接受痛苦吧，理解痛苦吧。",
    "沉醉在本大爷的美技中吧！",
    "我已经超脱人的极限了。",
    "你还差得远呢。",
    "不要停下来啊！",
    "我不做人啦，JOJO！",
    "砸瓦鲁多！时间停止吧！",
    "木大木大木大木大------！",
    "欧拉欧拉欧拉欧拉------！",
    "人被杀，就会死。",
    "错的不是我，错的是这个世界！",
    "你也想起舞吗？",
    "燃烧吧，我的小宇宙！",
    "这一切都是命运石之门的选择！",
    "我的王之力啊------！",
    "教练，我想打篮球！",
    "真相永远只有一个！",
    "无路赛！无路赛！无路赛！",
    "我命由我不由天！",
    "斗宗强者恐怖如斯。",
    "这个世界，就由我来收下了。",
    "燃烧心灵吧！",
]

ACTIONS = [
    "对镜子说三遍我是最棒的",
    "用播音腔朗读一段课文",
    "模仿一位动漫角色说话30秒",
    "对着空气大喊一句台词",
    "在群里发一条中二宣言",
    "做10个深蹲并喊出口号",
]

TARGETS = ["室友", "同桌", "手机镜头", "空气", "群聊", "家人"]

ACHIEVEMENTS = [
    ("streak_3", "三日自律", "badge", "streak", 3),
    ("streak_7", "七日自律", "badge", "streak", 7),
    ("streak_30", "月度自律", "title", "streak", 30),
    ("task_10", "初露锋芒", "title", "completed_tasks", 10),
    ("task_50", "小有所成", "title", "completed_tasks", 50),
    ("task_100", "百炼成钢", "title", "completed_tasks", 100),
    ("study_600", "十小时修行", "badge", "study_minutes", 600),
    ("study_3000", "五十小时", "badge", "study_minutes", 3000),
    ("ent_10", "中二入门", "badge", "ent_draws", 10),
    ("ent_50", "中二大师", "title", "ent_draws", 50),
]


# ============ 工具 ============
def now_str():
    return datetime.now().isoformat(timespec="seconds")


def today_str():
    return date.today().isoformat()


def parse_time(s):
    return datetime.strptime(s, "%H:%M").time()


def minutes_between(s, e):
    d1 = datetime.combine(datetime.today(), s)
    d2 = datetime.combine(datetime.today(), e)
    return int((d2 - d1).total_seconds() // 60)


def get_conn(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    conn = get_conn(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def db_run(db_path, sql, params=()):
    conn = get_conn(db_path)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def db_all(db_path, sql, params=()):
    conn = get_conn(db_path)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def db_one(db_path, sql, params=()):
    rows = db_all(db_path, sql, params)
    return rows[0] if rows else None


# ============ 课表 ============
def load_schedule(path):
    courses = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for values in reader:
            row = {}
            for i in range(len(header)):
                row[header[i]] = values[i] if i < len(values) else ""

            row["start"] = parse_time(row["start"])
            row["end"] = parse_time(row["end"])
            row["difficulty"] = int(row["difficulty"] or 3)
            row["credits"] = int(row["credits"] or 3)
            row["assignment_due"] = row["assignment_due"] or None
            row["exam_date"] = row["exam_date"] or None
            courses.append(row)
    return courses


def write_default_schedule():
    path = os.path.join(tempfile.gettempdir(), "task_system_schedule.csv")
    with open(path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_SCHEDULE)
    return path


def free_slots(classes):
    day_start = time(7, 0)
    day_end = time(23, 0)
    slots = [(day_start, day_end)]
    for c in sorted(classes, key=lambda x: x["start"]):
        new_slots = []
        for s, e in slots:
            if c["end"] <= s or c["start"] >= e:
                new_slots.append((s, e))
            else:
                if s < c["start"]:
                    new_slots.append((s, c["start"]))
                if c["end"] < e:
                    new_slots.append((c["end"], e))
        slots = new_slots
    result = []
    for s, e in slots:
        m = minutes_between(s, e)
        if m >= 30:
            result.append((s, e, m))
    return result


def allocate_blocks(courses, day):
    classes = [c for c in courses if c["day"] == day]
    free = free_slots(classes)

    scores = []
    for c in courses:
        score = c["difficulty"] * c["credits"]
        due = c.get("assignment_due")
        if due:
            try:
                d = datetime.strptime(due, "%Y-%m-%d")
                left = (d - datetime.today()).days
                if left < 7:
                    score += 5
                elif left < 14:
                    score += 2
            except Exception:
                pass
        scores.append((score, c))

    total = sum(s for s, _ in scores) or 1
    plan = []
    for s, e, length in free:
        blocks = max(1, length // 60)
        for b in range(blocks):
            r = random.uniform(0, total)
            acc = 0
            for sc, course in scores:
                acc += sc
                if r <= acc:
                    start_dt = datetime.combine(datetime.today(), s) + timedelta(minutes=60 * b)
                    end_dt = start_dt + timedelta(minutes=60)
                    plan.append({
                        "start": start_dt.strftime("%H:%M"),
                        "end": end_dt.strftime("%H:%M"),
                        "course": course["course"],
                        "difficulty": course["difficulty"],
                        "duration_min": 60,
                    })
                    break
    return plan


# ============ 奖励 ============
def task_reward(difficulty, duration_min):
    base = difficulty * (duration_min / 60.0)
    return round(min(REWARD_MAX, max(REWARD_MIN, base)), 2)


def daily_reward(ratio, tasks):
    if not tasks:
        return 0.0
    pool = sum(task_reward(t["difficulty"], t["duration_min"]) for t in tasks)
    per_tier = pool / len(REWARD_TIERS)
    reward = 0.0
    for tier in REWARD_TIERS:
        if ratio + 1e-9 >= tier:
            reward += per_tier
    return round(min(reward, DAILY_REWARD_CAP), 2)


# ============ 核心类 ============
class TaskSystem:
    def __init__(self, db_path="task_system.db", schedule_path=None):
        self.db_path = db_path
        self.schedule_path = schedule_path
        self.schedules = {}
        init_db(db_path)

    # ---- 用户 ----
    def register(self, user_id):
        exists = db_one(self.db_path, "SELECT * FROM users WHERE user_id=?", (user_id,))
        if exists:
            return exists
        db_run(self.db_path,
               "INSERT INTO users (user_id, created_at) VALUES (?, ?)",
               (user_id, now_str()))
        return self.get_user(user_id)

    def get_user(self, user_id):
        u = db_one(self.db_path, "SELECT * FROM users WHERE user_id=?", (user_id,))
        if not u:
            raise ValueError("user not found: " + str(user_id))
        return u

    # ---- 充值 ----
    def recharge(self, user_id, amount):
        if amount <= 0:
            raise ValueError("amount must be positive")
        u = self.get_user(user_id)
        stopped = bool(u["commission_stopped"])
        if stopped:
            commission = 0.0
            net = amount
        else:
            commission = round(amount * COMMISSION_RATE, 2)
            net = round(amount - commission, 2)
        new_balance = round(u["balance"] + net, 2)
        new_recharge = round(u["total_recharge"] + amount, 2)
        new_commission = round(u["total_commission"] + commission, 2)
        db_run(self.db_path,
               "UPDATE users SET balance=?, total_recharge=?, total_commission=? WHERE user_id=?",
               (new_balance, new_recharge, new_commission, user_id))
        db_run(self.db_path,
               "INSERT INTO recharges (user_id, amount, commission, net, created_at) VALUES (?, ?, ?, ?, ?)",
               (user_id, amount, commission, net, now_str()))
        return {
            "user_id": user_id,
            "amount": amount,
            "commission": commission,
            "net": net,
            "balance": new_balance,
            "commission_stopped": stopped,
        }

    # ---- 课表 ----
    def set_schedule(self, user_id, csv_path):
        courses = load_schedule(csv_path)
        self.schedules[user_id] = courses
        return len(courses)

    def _get_courses(self, user_id):
        if user_id not in self.schedules:
            path = self.schedule_path or write_default_schedule()
            self.schedules[user_id] = load_schedule(path)
        return self.schedules[user_id]

    # ---- 自律板块 ----
    def publish_daily_tasks(self, user_id, day=None):
        self.get_user(user_id)
        target = day or today_str()
        existing = db_all(self.db_path,
                          "SELECT * FROM study_tasks WHERE user_id=? AND date=? ORDER BY start",
                          (user_id, target))
        if existing:
            return existing

        courses = self._get_courses(user_id)
        weekday = datetime.fromisoformat(target).strftime("%a")
        if weekday not in DAYS:
            weekday = "Mon"

        blocks = allocate_blocks(courses, weekday)
        created = []
        for b in blocks:
            task_id = uuid.uuid4().hex[:12]
            reward = task_reward(b["difficulty"], b["duration_min"])
            db_run(self.db_path,
                   "INSERT INTO study_tasks (task_id, user_id, date, start, end, course, difficulty, duration_min, reward, status) "
                   "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')",
                   (task_id, user_id, target, b["start"], b["end"],
                    b["course"], b["difficulty"], b["duration_min"], reward))
            created.append(self._get_task(task_id))
        return created

    def _get_task(self, task_id):
        return db_one(self.db_path, "SELECT * FROM study_tasks WHERE task_id=?", (task_id,))

    def get_today_tasks(self, user_id, day=None):
        target = day or today_str()
        return db_all(self.db_path,
                      "SELECT * FROM study_tasks WHERE user_id=? AND date=? ORDER BY start",
                      (user_id, target))

    def complete_task(self, user_id, task_id):
        task = self._get_task(task_id)
        if not task or task["user_id"] != user_id:
            raise ValueError("task not found: " + str(task_id))
        if task["status"] == "done":
            return {"task_id": task_id, "status": "done", "already": True,
                    "reward_issued": 0.0, "new_achievements": []}

        db_run(self.db_path,
               "UPDATE study_tasks SET status='done', completed_at=? WHERE task_id=?",
               (now_str(), task_id))

        day_tasks = self.get_today_tasks(user_id, task["date"])
        done = [t for t in day_tasks if t["status"] == "done"]
        ratio = len(done) / len(day_tasks) if day_tasks else 0.0

        prev = db_one(self.db_path,
                      "SELECT * FROM daily_stats WHERE user_id=? AND date=?",
                      (user_id, task["date"]))
        prev_reward = prev["reward"] if prev else 0.0

        total_today = daily_reward(ratio, day_tasks)
        delta = round(max(0.0, total_today - prev_reward), 2)

        u = self.get_user(user_id)
        if delta > 0:
            new_balance = round(max(0.0, u["balance"] - delta), 2)
            new_total_reward = round(u["total_reward"] + delta, 2)
        else:
            new_balance = u["balance"]
            new_total_reward = u["total_reward"]

        new_completed = u["completed_tasks"] + 1
        new_streak = self._calc_streak(u, task["date"])
        stopped = 1 if new_completed >= COMMISSION_STOP_N else int(u["commission_stopped"])

        db_run(self.db_path,
               "UPDATE users SET balance=?, total_reward=?, completed_tasks=?, streak=?, "
               "last_complete_date=?, commission_stopped=? WHERE user_id=?",
               (new_balance, new_total_reward, new_completed, new_streak,
                task["date"], stopped, user_id))

        study_min = int(sum(t["duration_min"] for t in done))
        db_run(self.db_path,
               "INSERT OR REPLACE INTO daily_stats (user_id, date, completed_ratio, reward, study_minutes) "
               "VALUES (?, ?, ?, ?, ?)",
               (user_id, task["date"], ratio, total_today, study_min))

        newly = self._unlock_achievements(user_id)

        return {
            "task_id": task_id,
            "status": "done",
            "completed_ratio": ratio,
            "today_reward": total_today,
            "reward_issued": delta,
            "balance": new_balance,
            "completed_tasks": new_completed,
            "streak": new_streak,
            "commission_stopped": bool(stopped),
            "new_achievements": newly,
        }

    def _calc_streak(self, user, day):
        last = user["last_complete_date"]
        if not last:
            return 1
        try:
            d1 = datetime.fromisoformat(last).date()
            d2 = datetime.fromisoformat(day).date()
        except Exception:
            return 1
        diff = (d2 - d1).days
        if diff == 0:
            return user["streak"] or 1
        if diff == 1:
            return (user["streak"] or 0) + 1
        return 1

    # ---- 娱乐板块 ----
    def draw_entertainment(self, user_id):
        self.get_user(user_id)
        task_id = uuid.uuid4().hex[:12]
        line = random.choice(LINES)
        action = random.choice(ACTIONS)
        target = random.choice(TARGETS)
        db_run(self.db_path,
               "INSERT INTO entertainment_tasks (task_id, user_id, line, action, target, status, drawn_at) "
               "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
               (task_id, user_id, line, action, target, now_str()))
        return db_one(self.db_path,
                      "SELECT * FROM entertainment_tasks WHERE task_id=?", (task_id,))

    def complete_entertainment(self, user_id, task_id):
        row = db_one(self.db_path,
                     "SELECT * FROM entertainment_tasks WHERE task_id=?", (task_id,))
        if not row or row["user_id"] != user_id:
            raise ValueError("entertainment task not found: " + str(task_id))
        if row["status"] == "done":
            return {"task_id": task_id, "status": "done", "already": True,
                    "new_achievements": []}
        db_run(self.db_path,
               "UPDATE entertainment_tasks SET status='done', completed_at=? WHERE task_id=?",
               (now_str(), task_id))
        newly = self._unlock_achievements(user_id)
        return {"task_id": task_id, "status": "done", "new_achievements": newly}

    # ---- 成就 ----
    def _collect_stats(self, user_id):
        u = self.get_user(user_id)
        study = db_one(self.db_path,
                       "SELECT COALESCE(SUM(duration_min),0) AS total FROM study_tasks "
                       "WHERE user_id=? AND status='done'",
                       (user_id,))
        ent = db_one(self.db_path,
                     "SELECT COUNT(*) AS cnt FROM entertainment_tasks WHERE user_id=?",
                     (user_id,))
        return {
            "streak": u["streak"],
            "completed_tasks": u["completed_tasks"],
            "study_minutes": int(study["total"]) if study else 0,
            "ent_draws": int(ent["cnt"]) if ent else 0,
        }

    def _unlock_achievements(self, user_id):
        stats = self._collect_stats(user_id)
        unlocked = []
        for aid, name, atype, key, threshold in ACHIEVEMENTS:
            if stats.get(key, 0) < threshold:
                continue
            exists = db_one(self.db_path,
                            "SELECT 1 FROM achievements WHERE user_id=? AND achievement_id=?",
                            (user_id, aid))
            if exists:
                continue
            db_run(self.db_path,
                   "INSERT INTO achievements (user_id, achievement_id, name, type, unlocked_at) "
                   "VALUES (?, ?, ?, ?, ?)",
                   (user_id, aid, name, atype, now_str()))
            unlocked.append({"id": aid, "name": name, "type": atype})
        return unlocked

    def get_achievements(self, user_id):
        return db_all(self.db_path,
                      "SELECT achievement_id AS id, name, type, unlocked_at "
                      "FROM achievements WHERE user_id=? ORDER BY unlocked_at",
                      (user_id,))

    # ---- Dashboard ----
    def get_dashboard(self, user_id):
        u = self.get_user(user_id)
        today = today_str()
        tasks = self.get_today_tasks(user_id, today)
        done = [t for t in tasks if t["status"] == "done"]
        ratio = len(done) / len(tasks) if tasks else 0.0

        row = db_one(self.db_path,
                     "SELECT reward FROM daily_stats WHERE user_id=? AND date=?",
                     (user_id, today))
        today_reward = row["reward"] if row else 0.0

        study = db_one(self.db_path,
                       "SELECT COALESCE(SUM(duration_min),0) AS total FROM study_tasks "
                       "WHERE user_id=? AND status='done'",
                       (user_id,))
        total_study = int(study["total"]) if study else 0

        dist_rows = db_all(self.db_path,
                           "SELECT course, SUM(duration_min) AS minutes FROM study_tasks "
                           "WHERE user_id=? AND status='done' GROUP BY course",
                           (user_id,))
        course_dist = {}
        for r in dist_rows:
            course_dist[r["course"]] = int(r["minutes"] or 0)

        count_row = db_one(self.db_path,
                           "SELECT COUNT(*) AS cnt FROM study_tasks WHERE user_id=?",
                           (user_id,))
        total_assigned = int(count_row["cnt"]) if count_row else 0
        completion_rate = u["completed_tasks"] / total_assigned if total_assigned else 0.0

        ent_rows = db_all(self.db_path,
                          "SELECT task_id, line, action, target, status, drawn_at, completed_at "
                          "FROM entertainment_tasks WHERE user_id=? ORDER BY drawn_at DESC LIMIT 50",
                          (user_id,))
        ent_count_row = db_one(self.db_path,
                               "SELECT COUNT(*) AS cnt FROM entertainment_tasks WHERE user_id=?",
                               (user_id,))
        ent_count = int(ent_count_row["cnt"]) if ent_count_row else 0

        return {
            "user_id": user_id,
            "total_reward": round(u["total_reward"], 2),
            "today": {
                "date": today,
                "tasks": tasks,
                "completed_ratio": ratio,
                "today_reward": today_reward,
            },
            "streak": u["streak"],
            "completed_tasks": u["completed_tasks"],
            "total_study_minutes": total_study,
            "completion_rate": round(completion_rate, 3),
            "course_distribution": course_dist,
            "entertainment": {
                "draw_count": ent_count,
                "history": ent_rows,
            },
            "achievements": self.get_achievements(user_id),
        }


# ============ JSON 接口 ============
_default_skill = None


def get_skill():
    global _default_skill
    if _default_skill is None:
        _default_skill = TaskSystem()
    return _default_skill


def handle(payload):
    skill = get_skill()
    action = payload.get("action")
    uid = payload.get("user_id")
    try:
        if action == "register":
            return {"ok": True, "data": skill.register(uid)}
        if action == "recharge":
            return {"ok": True, "data": skill.recharge(uid, float(payload["amount"]))}
        if action == "set_schedule":
            return {"ok": True, "data": {"courses": skill.set_schedule(uid, payload["csv_path"])}}
        if action == "publish_daily_tasks":
            return {"ok": True, "data": skill.publish_daily_tasks(uid, payload.get("date"))}
        if action == "complete_task":
            return {"ok": True, "data": skill.complete_task(uid, payload["task_id"])}
        if action == "get_today_tasks":
            return {"ok": True, "data": skill.get_today_tasks(uid, payload.get("date"))}
        if action == "draw_entertainment_task":
            return {"ok": True, "data": skill.draw_entertainment(uid)}
        if action == "complete_entertainment_task":
            return {"ok": True, "data": skill.complete_entertainment(uid, payload["task_id"])}
        if action == "get_dashboard":
            return {"ok": True, "data": skill.get_dashboard(uid)}
        if action == "get_achievements":
            return {"ok": True, "data": skill.get_achievements(uid)}
        return {"ok": False, "error": "unknown action: " + str(action)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============ 演示 ============
def demo():
    db_file = "demo_task_system.db"
    if os.path.exists(db_file):
        os.remove(db_file)

    skill = TaskSystem(db_path=db_file)
    print("注册:", skill.register("u1")["user_id"])
    print("充值:", skill.recharge("u1", 100))

    tasks = skill.publish_daily_tasks("u1")
    print("今日任务数:", len(tasks))

    if tasks:
        print("完成第一个:", skill.complete_task("u1", tasks[0]["task_id"]))
    if len(tasks) > 1:
        print("完成第二个:", skill.complete_task("u1", tasks[1]["task_id"]))

    ent = skill.draw_entertainment("u1")
    print("娱乐抽取:", ent["line"], "|", ent["action"], "|", ent["target"])
    print("娱乐完成:", skill.complete_entertainment("u1", ent["task_id"]))

    print("\nDashboard:")
    print(json.dumps(skill.get_dashboard("u1"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
