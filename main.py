import asyncio
import logging
import os
import random
import re
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "nuolinga.db")
TIMEZONE_NAME = os.getenv("TIMEZONE", "UTC")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing in .env")

try:
    APP_TZ = ZoneInfo(TIMEZONE_NAME)
except Exception:
    APP_TZ = timezone.utc

logging.basicConfig(level=logging.INFO)
dp = Dispatcher(storage=MemoryStorage())

TEXTS = {
 "ru": {
  "select_language":"Select language / выберите язык",
  "welcome":"Привет, я Nuo 👋\n\nЗдесь ты можешь решать задания по математике и получать за это опыт. За опыт ты получаешь уровни и сражаешься в таблице лидеров по уровню.",
  "play":"🎮 Играть","leaders":"🏆 Таблица лидеров","profile_btn":"👤 Профиль","achievements_btn":"🏅 Достижения",
  "choose_class":"Выбери класс. Чем выше класс, тем сложнее задания и больше опыта:",
  "class":"📚 {grade} класс","question":"🧮 Задание для {grade} класса:\n\n{question}\n\nНапиши только ответ.",
  "correct":"✅ Правильно! +{xp} XP\nУровень: {level}\n🔥 Серия правильных ответов: {streak}\n📅 Серия дней: {daily}",
  "wrong":"❌ Неправильно.\nПравильный ответ: {answer}\nСерия правильных ответов сброшена.",
  "next":"➡️ Следующее задание","back":"⬅️ В меню","no_players":"Пока игроков нет.",
  "invalid":"Напиши число, например: 42","profile":"👤 {name}{verified}\n⭐ Уровень: {level}\n✨ XP: {xp}\n🔥 Серия ответов: {streak}\n📅 Серия дней: {daily}",
  "top":"{pos}. {name}{verified} — Lv.{level} — {xp} XP",
  "ach_title":"🏅 Достижения","ach_unlocked":"✅","ach_locked":"🔒",
  "verify_denied":"Эту команду может использовать только @PlatoKiri_tg.",
  "verify_usage":"Использование: /verify USER_ID или /verify @username — выдать галочку игроку.",
  "verify_done":"✅ Галочка выдана пользователю {uid}.","verify_not_found":"Игрок не найден. Пусть он сначала нажмёт /start.",
  "verified":" ☑️","menu":"Главное меню"
 },
 "en": {
  "select_language":"Select language / выберите язык",
  "welcome":"Hi, I'm Nuo 👋\n\nHere you can solve math problems and earn XP. XP gives you levels, and you can compete on the leaderboard.",
  "play":"🎮 Play","leaders":"🏆 Leaderboard","profile_btn":"👤 Profile","achievements_btn":"🏅 Achievements",
  "choose_class":"Choose a grade. Higher grades have harder tasks and give more XP:",
  "class":"📚 Grade {grade}","question":"🧮 Grade {grade} problem:\n\n{question}\n\nSend only the answer.",
  "correct":"✅ Correct! +{xp} XP\nLevel: {level}\n🔥 Correct-answer streak: {streak}\n📅 Day streak: {daily}",
  "wrong":"❌ Incorrect.\nCorrect answer: {answer}\nCorrect-answer streak reset.",
  "next":"➡️ Next problem","back":"⬅️ Menu","no_players":"No players yet.",
  "invalid":"Send a number, for example: 42","profile":"👤 {name}{verified}\n⭐ Level: {level}\n✨ XP: {xp}\n🔥 Answer streak: {streak}\n📅 Day streak: {daily}",
  "top":"{pos}. {name}{verified} — Lv.{level} — {xp} XP",
  "ach_title":"🏅 Achievements","ach_unlocked":"✅","ach_locked":"🔒",
  "verify_denied":"Only @PlatoKiri_tg can use this command.",
  "verify_usage":"Usage: /verify USER_ID or /verify @username — give a verification badge.",
  "verify_done":"✅ Verification badge granted to user {uid}.","verify_not_found":"Player not found. Ask them to send /start first.",
  "verified":" ☑️","menu":"Main menu"
 },
 "zh": {
  "select_language":"Select language / 选择语言",
  "welcome":"你好，我是 Nuo 👋\n\n在这里你可以解决数学题并获得经验值。经验值可以提升等级，还可以在排行榜上与其他玩家竞争。",
  "play":"🎮 开始游戏","leaders":"🏆 排行榜","profile_btn":"👤 个人资料","achievements_btn":"🏅 成就",
  "choose_class":"选择年级。年级越高，题目越难，获得的经验越多：",
  "class":"📚 {grade} 年级","question":"🧮 {grade} 年级题目：\n\n{question}\n\n只发送答案。",
  "correct":"✅ 正确！+{xp} XP\n等级：{level}\n🔥 连续答对：{streak}\n📅 连续活跃天数：{daily}",
  "wrong":"❌ 错误。\n正确答案：{answer}\n连续答对次数已重置。",
  "next":"➡️ 下一题","back":"⬅️ 返回菜单","no_players":"还没有玩家。",
  "invalid":"请输入数字，例如：42","profile":"👤 {name}{verified}\n⭐ 等级：{level}\n✨ XP：{xp}\n🔥 连续答对：{streak}\n📅 连续活跃天数：{daily}",
  "top":"{pos}. {name}{verified} — Lv.{level} — {xp} XP",
  "ach_title":"🏅 成就","ach_unlocked":"✅","ach_locked":"🔒",
  "verify_denied":"只有 @PlatoKiri_tg 可以使用此命令。",
  "verify_usage":"用法：/verify USER_ID 或 /verify @username — 授予认证标记。",
  "verify_done":"✅ 已为用户 {uid} 授予认证标记。","verify_not_found":"未找到玩家。请让对方先发送 /start。",
  "verified":" ☑️","menu":"主菜单"
 }
}

XP_BY_GRADE = {2:10, 4:20, 6:35, 9:60, 11:100}
ACHIEVEMENTS = {
 "night_owl": ("Не спящий", "Решить 5 примеров с 00:00 до 02:05", "Solve 5 problems between 00:00 and 02:05"),
 "lost_streak": ("Не везучий", "Потерять серию в 25 дней", "Lose a 25-day streak"),
 "streak_5": ("В яблочко", "Серия правильных ответов — 5", "Reach a correct-answer streak of 5"),
 "streak_52": ("Друг Nuo", "Серия правильных ответов — 52", "Reach a correct-answer streak of 52"),
 "streak_111": ("Золотое яблочко", "Серия правильных ответов — 111", "Reach a correct-answer streak of 111"),
 "verified": ("Галочка!", "Получить галочку в профиль", "Get a verification badge"),
 "days_30": ("Постоянный клиент", "Достичь серии в 30 дней", "Reach a 30-day streak"),
 "days_67": ("С читами", "Достичь серии в 67 дней", "Reach a 67-day streak"),
}

class GameState(StatesGroup):
    answering = State()

def t(lang, key):
    return TEXTS.get(lang, TEXTS["ru"])[key]

def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text="🇷🇺 Russian / Русский", callback_data="lang:ru")],
      [InlineKeyboardButton(text="🇬🇧 English / Английский", callback_data="lang:en")],
      [InlineKeyboardButton(text="🇨🇳 Chinese / 中文", callback_data="lang:zh")]
    ])

def main_menu(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text=t(lang,"play"), callback_data="menu:play")],
      [InlineKeyboardButton(text=t(lang,"profile_btn"), callback_data="menu:profile"),
       InlineKeyboardButton(text=t(lang,"achievements_btn"), callback_data="menu:achievements")],
      [InlineKeyboardButton(text=t(lang,"leaders"), callback_data="menu:leaders")]
    ])

def class_menu(lang):
    b=InlineKeyboardBuilder()
    for grade in (2,4,6,9,11):
        b.button(text=t(lang,"class").format(grade=grade), callback_data=f"grade:{grade}")
    b.adjust(2)
    b.row(InlineKeyboardButton(text=t(lang,"back"), callback_data="menu:back"))
    return b.as_markup()

def result_menu(lang):
    return InlineKeyboardMarkup(inline_keyboard=[
      [InlineKeyboardButton(text=t(lang,"next"), callback_data="next")],
      [InlineKeyboardButton(text=t(lang,"back"), callback_data="menu:back")]
    ])

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, name TEXT NOT NULL, username TEXT,
          lang TEXT NOT NULL DEFAULT 'ru',
          xp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 1,
          correct_streak INTEGER NOT NULL DEFAULT 0, best_correct_streak INTEGER NOT NULL DEFAULT 0,
          daily_streak INTEGER NOT NULL DEFAULT 0, last_active_date TEXT,
          night_solved INTEGER NOT NULL DEFAULT 0, verified INTEGER NOT NULL DEFAULT 0
        )""")
        # Migrate existing databases created by the previous Nuolinga version.
        cur=await db.execute("PRAGMA table_info(users)")
        columns={row[1] for row in await cur.fetchall()}
        additions={
          "username":"TEXT",
          "correct_streak":"INTEGER NOT NULL DEFAULT 0",
          "best_correct_streak":"INTEGER NOT NULL DEFAULT 0",
          "daily_streak":"INTEGER NOT NULL DEFAULT 0",
          "last_active_date":"TEXT",
          "night_solved":"INTEGER NOT NULL DEFAULT 0",
          "verified":"INTEGER NOT NULL DEFAULT 0",
        }
        for col, definition in additions.items():
            if col not in columns:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
        await db.execute("""CREATE TABLE IF NOT EXISTS user_achievements(
          user_id INTEGER NOT NULL, achievement_id TEXT NOT NULL, unlocked_at TEXT NOT NULL,
          PRIMARY KEY(user_id, achievement_id)
        )""")
        await db.commit()

async def upsert_user(user_id, name, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""INSERT INTO users(user_id,name,username) VALUES(?,?,?)
          ON CONFLICT(user_id) DO UPDATE SET
          name=excluded.name, username=excluded.username""",
          (user_id, name, username.lower() if username else None))
        await db.commit()

async def get_user(uid):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM users WHERE user_id=?",(uid,))
        r=await cur.fetchone()
        return dict(r) if r else None

async def set_language(uid, lang):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET lang=? WHERE user_id=?",(lang,uid)); await db.commit()

async def unlock(uid, aid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO user_achievements VALUES(?,?,?)",
                         (uid,aid,datetime.now(APP_TZ).isoformat()))
        await db.commit()

async def has_achievement(uid, aid):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id=?",(uid,aid))
        return await cur.fetchone() is not None

async def evaluate_streak_achievements(uid, streak, daily):
    for threshold, aid in [(5,"streak_5"),(52,"streak_52"),(111,"streak_111")]:
        if streak >= threshold: await unlock(uid,aid)
    for threshold, aid in [(30,"days_30"),(67,"days_67")]:
        if daily >= threshold: await unlock(uid,aid)

async def record_answer(uid, correct, grade):
    """Update XP/streaks only for a submitted numeric answer."""
    now=datetime.now(APP_TZ)
    today=now.date()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM users WHERE user_id=?",(uid,))
        row=dict(await cur.fetchone())
        previous=row["last_active_date"]
        daily=row["daily_streak"]
        lost_25=False
        if previous:
            prev_date=date.fromisoformat(previous)
            gap=(today-prev_date).days
            if gap > 1:
                if daily >= 25: lost_25=True
                daily=1
            elif gap == 1:
                daily += 1
            # same date leaves daily unchanged
        else:
            daily=1

        streak=row["correct_streak"]
        best=row["best_correct_streak"]
        xp=row["xp"]
        night=row["night_solved"]
        if correct:
            streak += 1
            best=max(best,streak)
            xp += XP_BY_GRADE[grade]
            if (now.hour == 0 or (now.hour == 2 and now.minute <= 5) or now.hour == 1):
                night += 1
        else:
            streak=0
        level=xp//100+1
        await db.execute("""UPDATE users SET xp=?,level=?,correct_streak=?,best_correct_streak=?,
          daily_streak=?,last_active_date=?,night_solved=? WHERE user_id=?""",
          (xp,level,streak,best,daily,today.isoformat(),night,uid))
        await db.commit()
    if lost_25: await unlock(uid,"lost_streak")
    if night >= 5: await unlock(uid,"night_owl")
    await evaluate_streak_achievements(uid,streak,daily)
    return {"xp":XP_BY_GRADE[grade],"level":level,"streak":streak,"daily":daily}

async def top_players(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT name,xp,level,verified FROM users ORDER BY level DESC,xp DESC LIMIT ?",(limit,))
        return await cur.fetchall()

async def achievements_text(uid, lang):
    unlocked=set()
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT achievement_id FROM user_achievements WHERE user_id=?",(uid,))
        unlocked={r[0] for r in await cur.fetchall()}
    lines=[t(lang,"ach_title"),""]
    for aid,(name,ru_desc,en_desc) in ACHIEVEMENTS.items():
        if lang=="zh":
            descriptions={
             "night_owl":"在 00:00 到 02:05 之间解答 5 道题","lost_streak":"失去 25 天连续活跃记录",
             "streak_5":"连续答对 5 题","streak_52":"连续答对 52 题","streak_111":"连续答对 111 题",
             "verified":"获得个人资料认证标记","days_30":"达到 30 天连续活跃","days_67":"达到 67 天连续活跃"}
            label={"night_owl":"夜猫子","lost_streak":"运气不好","streak_5":"正中靶心","streak_52":"Nuo 的朋友","streak_111":"金苹果","verified":"认证标记！","days_30":"常客","days_67":"开挂了"}
            title=label[aid]; desc=descriptions[aid]
        else:
            title=name if lang=="ru" else {
             "night_owl":"Night Owl","lost_streak":"Unlucky","streak_5":"Bullseye","streak_52":"Nuo's Friend",
             "streak_111":"Golden Apple","verified":"Verified!","days_30":"Regular","days_67":"Cheater"
            }[aid]
            desc=ru_desc if lang=="ru" else en_desc
        mark=t(lang,"ach_unlocked") if aid in unlocked else t(lang,"ach_locked")
        lines.append(f"{mark} **{title}** — {desc}")
    return "\n".join(lines)

def make_question(grade):
    if grade == 2:
        a=random.randint(10,99); b=random.randint(1,50)
        if random.choice([True,False]): return f"{a} + {b} = ?",a+b
        a=random.randint(30,99); b=random.randint(1,a); return f"{a} − {b} = ?",a-b
    if grade == 4:
        mode=random.choice(["mul","div","add"])
        if mode=="mul":
            a,b=random.randint(10,99),random.randint(2,12); return f"{a} × {b} = ?",a*b
        if mode=="div":
            b,ans=random.randint(2,12),random.randint(2,20); return f"{b*ans} ÷ {b} = ?",ans
        a,b=random.randint(100,999),random.randint(100,999); return f"{a} + {b} = ?",a+b
    if grade == 6:
        if random.choice([True,False]):
            pct=random.choice([10,20,25,50]); n=random.choice([40,60,80,120,200,240])
            return f"{pct}% of {n} = ?",n*pct//100
        a,x,b=random.randint(2,12),random.randint(2,20),random.randint(1,20)
        return f"{a}x + {b} = {a*x+b}. x = ?",x
    if grade == 9:
        a,x,b=random.randint(2,12),random.randint(-10,10),random.randint(-20,20)
        c=a*x+b; sign="+" if b>=0 else "−"
        return f"{a}x {sign} {abs(b)} = {c}. x = ?",x
    # Grade 11: quadratic equations with integer roots.
    r1=random.randint(-8,8); r2=random.randint(-8,8)
    b=-(r1+r2); c=r1*r2
    sign_b="+" if b>=0 else "−"; sign_c="+" if c>=0 else "−"
    return f"x² {sign_b} {abs(b)}x {sign_c} {abs(c)} = 0. Give the larger root.",max(r1,r2)

async def send_question(message,state,lang,grade):
    question,answer=make_question(grade)
    await state.set_state(GameState.answering)
    await state.update_data(grade=grade,answer=answer)
    await message.answer(t(lang,"question").format(grade=grade,question=question),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                           [InlineKeyboardButton(text=t(lang,"back"),callback_data="menu:back")]]))

@dp.message(CommandStart())
async def start(message:Message,state:FSMContext):
    await state.clear()
    u=message.from_user
    await upsert_user(u.id, u.full_name or u.username or "Player", u.username)
    await message.answer(TEXTS["ru"]["select_language"],reply_markup=language_keyboard())

@dp.callback_query(F.data.startswith("lang:"))
async def choose_language(c:CallbackQuery,state:FSMContext):
    lang=c.data.split(":")[1]
    await set_language(c.from_user.id,lang); await state.clear(); await c.answer()
    if c.message: await c.message.edit_text(t(lang,"welcome"),reply_markup=main_menu(lang))

@dp.callback_query(F.data=="menu:play")
async def play(c:CallbackQuery):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"; await c.answer()
    if c.message: await c.message.edit_text(t(lang,"choose_class"),reply_markup=class_menu(lang))

@dp.callback_query(F.data.startswith("grade:"))
async def grade(c:CallbackQuery,state:FSMContext):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"
    g=int(c.data.split(":")[1]); await c.answer()
    if c.message: await send_question(c.message,state,lang,g)

@dp.callback_query(F.data=="next")
async def next_q(c:CallbackQuery,state:FSMContext):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"
    data=await state.get_data(); g=int(data.get("grade",2)); await c.answer()
    if c.message: await send_question(c.message,state,lang,g)

@dp.message(GameState.answering)
async def answer(message:Message,state:FSMContext):
    u=await get_user(message.from_user.id); lang=u["lang"] if u else "ru"
    data=await state.get_data()
    try: value=float(message.text.strip().replace(",","."))
    except (AttributeError,ValueError):
        await message.answer(t(lang,"invalid")); return
    expected=float(data["answer"]); g=int(data["grade"]); correct=abs(value-expected)<1e-9
    if correct:
        stats=await record_answer(message.from_user.id,True,g)
        await message.answer(t(lang,"correct").format(**stats),reply_markup=result_menu(lang))
    else:
        await record_answer(message.from_user.id,False,g)
        await message.answer(t(lang,"wrong").format(answer=data["answer"]),reply_markup=result_menu(lang))

@dp.callback_query(F.data=="menu:back")
async def back(c:CallbackQuery,state:FSMContext):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"
    await state.clear(); await c.answer()
    if c.message: await c.message.edit_text(t(lang,"welcome"),reply_markup=main_menu(lang))

@dp.callback_query(F.data=="menu:profile")
async def profile_button(c:CallbackQuery):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"; await c.answer()
    if not u: return
    await c.message.edit_text(t(lang,"profile").format(name=u["name"],verified=t(lang,"verified") if u["verified"] else "",
      level=u["level"],xp=u["xp"],streak=u["correct_streak"],daily=u["daily_streak"]),
      reply_markup=main_menu(lang))

@dp.message(Command("profile"))
async def profile_command(m:Message):
    u=await get_user(m.from_user.id)
    if not u: await m.answer("Use /start first."); return
    lang=u["lang"]
    await m.answer(t(lang,"profile").format(name=u["name"],verified=t(lang,"verified") if u["verified"] else "",
      level=u["level"],xp=u["xp"],streak=u["correct_streak"],daily=u["daily_streak"]),
      reply_markup=main_menu(lang))

@dp.callback_query(F.data=="menu:achievements")
async def achievement_button(c:CallbackQuery):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"; await c.answer()
    await c.message.edit_text(await achievements_text(c.from_user.id,lang),reply_markup=main_menu(lang))

@dp.callback_query(F.data=="menu:leaders")
async def leaders(c:CallbackQuery):
    u=await get_user(c.from_user.id); lang=u["lang"] if u else "ru"; rows=await top_players()
    await c.answer()
    if not rows: text=t(lang,"no_players")
    else:
        lines=[t(lang,"leaders"),""]
        for i,r in enumerate(rows,1):
            lines.append(t(lang,"top").format(pos=i,name=r[0],level=r[2],xp=r[1],verified=t(lang,"verified") if r[3] else ""))
        text="\n".join(lines)
    await c.message.edit_text(text,reply_markup=main_menu(lang))

@dp.message(Command("verify"))
async def verify(m:Message):
    admin_username=(m.from_user.username or "").lower()
    if admin_username!="platokiri_tg":
        u=await get_user(m.from_user.id); lang=u["lang"] if u else "ru"
        await m.answer(t(lang,"verify_denied")); return

    parts=(m.text or "").split(maxsplit=1)
    if len(parts)!=2 or not parts[1].strip():
        u=await get_user(m.from_user.id); lang=u["lang"] if u else "ru"
        await m.answer(t(lang,"verify_usage")); return

    target_arg=parts[1].strip()
    async with aiosqlite.connect(DB_PATH) as db:
        if target_arg.isdigit():
            cur=await db.execute("SELECT user_id FROM users WHERE user_id=?", (int(target_arg),))
        else:
            target_username=target_arg.removeprefix("@").strip().lower()
            if not target_username or not re.fullmatch(r"[a-z0-9_]{5,32}", target_username):
                u=await get_user(m.from_user.id); lang=u["lang"] if u else "ru"
                await m.answer(t(lang,"verify_usage")); return
            cur=await db.execute("SELECT user_id FROM users WHERE lower(username)=?", (target_username,))
        found=await cur.fetchone()
        if not found:
            u=await get_user(m.from_user.id); lang=u["lang"] if u else "ru"
            await m.answer(t(lang,"verify_not_found")); return
        target=int(found[0])
        await db.execute("UPDATE users SET verified=1 WHERE user_id=?", (target,))
        await db.commit()

    await unlock(target,"verified")
    u=await get_user(m.from_user.id); lang=u["lang"] if u else "ru"
    await m.answer(t(lang,"verify_done").format(uid=target))

async def main():
    await init_db()
    bot=Bot(BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    try: await dp.start_polling(bot)
    finally: await bot.session.close()

if __name__=="__main__":
    asyncio.run(main())
