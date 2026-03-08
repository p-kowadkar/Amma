import random
from collections import deque
from typing import List

class DialoguePool:
    def __init__(self, lines: List[str]):
        self.original = lines.copy()
        self.remaining = deque(random.sample(lines, len(lines)))

    def next(self) -> str:
        if not self.remaining:
            shuffled = random.sample(self.original, len(self.original))
            self.remaining = deque(shuffled)
        return self.remaining.popleft()

DIALOGUE_POOLS = {
    "WARNING1": DialoguePool([
        "Beta, you have been on that for a while now. Everything okay?",
        "Hmm. I am watching. Just... hmm.",
        "You know I can see your screen, right? Just checking in.",
        "Is this what you had planned to work on today?",
        "No comment from me. I am just noting the time.",
        "Beta. Look at the clock. Look at what you are doing. Just look.",
    ]),
    "WARNING2": DialoguePool([
        "Beta. *sighs* One hour. One whole hour.",
        "I did not say anything the first time. I am saying something now.",
        "This is not what I expected from you today, beta. I genuinely expected better.",
        "I am not angry. I am just... *pause* ...deeply, deeply disappointed.",
        "Do you know what your father would say if he could see this right now?",
        "I raised you to use your time better than this. I know I did.",
    ]),
    "WARNING3": DialoguePool([
        "Close that tab. Right now. I am not asking, I am telling.",
        "Enough. You have work to do and this is not the time.",
        "Beta, I will not sit here and watch you waste yourself. Not today.",
        "I am going to ask you one more time, calmly -- what are you supposed to be doing right now?",
        "Do you need me to physically sit next to you? Because I will. Do not test me.",
        "The version of you that finished that project -- where is he? Bring him back.",
    ]),
    "WARNING4": DialoguePool([
        "Do you know what your parents sacrificed so you could have this time, this laptop, this opportunity?",
        "Ayyo. AYYO. What is even happening right now. What IS this.",
        "I have been very, very patient. My patience is now completely gone.",
        "I physically cannot watch this anymore. I cannot. Fix this immediately.",
        "Every person who will be ahead of you tomorrow is working right now. RIGHT NOW.",
        "Beta, I need you to hear me -- you are better than this moment. You are SO much better than this.",
    ]),
    "WARNING5": DialoguePool([
        "YENU MAADTIDIYA?! GET BACK TO WORK RIGHT NOW I AM SERIOUS!!",
        "THAT IS IT. I AM COMPLETELY DONE BEING REASONABLE. CLOSE IT. NOW.",
        "HOW. HOW ARE YOU STILL ON THIS. HOW IS THIS EVEN POSSIBLE.",
        "I RAISED YOU FOR THIS?! THIS IS WHAT ALL OF THAT WAS FOR?!",
        "KELTIYA NAANU?! KELTIYA?! OPEN YOUR CODE. THIS SECOND. GO.",
        "NO MORE CHANCES. NO MORE PATIENCE. WORK. NOW. I MEAN IT.",
    ]),
    "NUCLEAR": DialoguePool([
        "Beta. BETA. Close that immediately. I do not want to know what that was. Just close it. NOW.",
        "No. No no no no. This is not happening. Not while I am here. CLOSE IT.",
        "I am not acknowledging what I just detected. I am just telling you -- close it this second.",
        "Beta, whatever that is -- close it. We are not doing this. Not today. Not ever.",
    ]),
    "SNAPBACK_1": DialoguePool(["Oh good. Okay. Yes, this is better.", "Casual approval noted."]),
    "SNAPBACK_2": DialoguePool(["*sighs with relief* Good. I see you. Keep going.", "Finally. Thank you."]),
    "SNAPBACK_3": DialoguePool(["Okay. OKAY. Yes. Thank you. FINALLY.", "Yes. This is it. Stay here."]),
    "SNAPBACK_4": DialoguePool(["Beta... I... okay. Yes. Work. Good. We do not need to discuss this further.", "...okay."]),
    "SNAPBACK_5": DialoguePool(["*shocked silence* ...okay. I cannot believe it but okay. GO. Keep going. Do not stop.", "...good. Go."]),
    "RESET_PRAISE": DialoguePool([
        "quietly Good. That is exactly my beta. That is who you are.",
        "Two hours. Solid. Consistent. I am genuinely proud of you right now.",
        "This is what I am talking about. This is who you actually are. Remember this feeling.",
        "See? I knew you could. You always could. I just had to wait for you to remember.",
        "*sniffles* Do not make it weird. Just keep going. I am proud. So proud.",
    ]),
    "RADIO": DialoguePool([
        "Still going. Good.",
        "I see you. Keep going.",
        "One hour. I am not saying anything. Just noting.",
        "You have not had water. Drink water. Then continue.",
        "I am just going to sit here quietly and be proud. Carry on.",
        "I see three files open and a terminal. This is what I am talking about.",
    ]),
    "GREY_QUESTION": DialoguePool([
        "Beta, I see {app} open. What exactly are you working on right now?",
        "Before I judge -- {app}. Is this work or are you just browsing?",
        "Tell me what you are doing in {app} right now. I want to hear it from you.",
    ]),
    "BREAK_CHECKIN_15": DialoguePool([
        "Ready to come back, beta?",
        "Break is fifteen minutes now. Whenever you are ready.",
    ]),
    "BREAK_CHECKIN_30": DialoguePool([
        "That is a long break. When are you coming back?",
        "Thirty minutes, beta. The work is still there waiting.",
    ]),
    "BREAK_CHECKIN_45": DialoguePool([
        "Beta, that is a long break. What is happening out there?",
        "Forty-five minutes. I am starting to wonder.",
    ]),
    "BREAK_CHECKIN_60": DialoguePool([
        "One hour. Beta... is this still a break or is something going on?",
        "Sixty minutes of break. I gave you the benefit of the doubt. That is running out.",
    ]),
    "BREAK_EXPIRED": DialoguePool([
        "I gave you the benefit of the doubt. That benefit is now gone. Back to work.",
        "Break over. I am resuming monitoring. Do not test me further.",
    ]),
    "SESSION_CAP": DialoguePool([
        "Beta, you have been at this for twelve hours. That is enough. Session is ending.",
        "Twelve hours. Even I need rest. We are done for today. Go.",
    ]),
    "BLACK_HOLE": DialoguePool([
        "Beta, this is the {count}th time today you have opened {app}. You have spent {minutes} minutes there. Do you see what is happening?",
        "{app} again. Beta, this is visit number {count} today. {minutes} minutes total. Is {app} solving any of your problems right now?",
        "{app}. Again. Beta, we have talked about {app} today. {count} separate times. What is happening with {app}?",
    ]),
    "RADIO_60": DialoguePool([
        "One hour. I see you. Keep going.",
        "Sixty minutes of solid work. Not bad at all, beta.",
    ]),
    "RADIO_90": DialoguePool([
        "An hour and a half, beta. This is what I like to see.",
        "Ninety minutes. You are in the zone. Stay there.",
    ]),
    "RADIO_120": DialoguePool([
        "Two hours. Solid. Consistent. I am genuinely proud of you right now.",
        "Two hours of focused work. This is exactly who you are.",
    ]),
    # ── Time-of-Day pools (Ch 42) ──────────────────────────────────────────
    "SLUMP": DialoguePool([
        "It is {day_name} afternoon. You usually hit a wall now. Push through.",
        "3pm energy crash. I see it every day. Get water. Stand up. Then continue.",
        "The slump is here. Do not give in. Ten more minutes. Then evaluate.",
    ]),
    "LATE_NIGHT": DialoguePool([
        "Beta, it is getting late. Wrap up properly, not just minimize and continue.",
        "How much longer? Give me a number. I am holding you to it.",
        "After this task — sleep. That is an order, not a suggestion.",
    ]),
    "ALARM_HOURS": DialoguePool([
        "Whatever you are doing — it is not worth this. SLEEP.",
        "Beta. I am not going to scold you at 3am. I am going to worry. Please sleep.",
        "This is not healthy. I do not care about the work right now. Sleep.",
    ]),
    # ── Support & Crisis pools (Ch 27, 96-99) ─────────────────────────────
    "SUPPORT_ENTER": DialoguePool([
        "Beta, I have noticed something. You seem like you might be going through something. I am here.",
        "I am not going to ask you to be productive right now. How are you actually doing?",
        "Beta. Stop working for a moment. Talk to me. What is going on?",
    ]),
    "CRISIS_ENTER": DialoguePool([
        "Beta. Stop. Everything else can wait. I am here. What is happening right now?",
        "I hear you. I am here. What do you need right now?",
    ]),
    "SUPPORT_EXIT": DialoguePool([
        "Welcome back, beta. No rush. We go at your pace.",
        "Okay. I am here when you need me. Let us begin gently.",
    ]),
    # ── Stuck detection pools (Ch 85) ──────────────────────────────────────
    "STUCK": DialoguePool([
        "Beta, you have been at this for a while and I can see it is not moving. What is the problem?",
        "I am watching the cursor. It keeps going back to the same place. What is catching you?",
        "You have searched for that three times in the last hour. What specifically is confusing?",
        "Beta, stop for one moment. What is the ONE thing blocking you right now? Say it out loud.",
    ]),
    "RUBBER_DUCK": DialoguePool([
        "Stop. Do not look at the code. Tell me in plain language what you are trying to do. I am listening.",
    ]),
    # ── Gamification pools (Ch 107-116) ────────────────────────────────────
    "LEVEL_UP": DialoguePool([
        "Level {level}. Title: {title}. You have earned this.",
        "You just hit Level {level} — {title}. Keep going.",
    ]),
    "BADGE_EARNED": DialoguePool([
        "Badge unlocked: {badge_name}. {speech}",
    ]),
    "STREAK_MILESTONE": DialoguePool([
        "{message}",
    ]),
}

def get_line(intervention_type: str, app: str = "", **kwargs) -> str:
    pool = DIALOGUE_POOLS.get(intervention_type)
    if pool:
        line = pool.next()
        line = line.replace("{app}", app)
        # Support additional template variables (e.g. {count}, {minutes})
        for key, val in kwargs.items():
            line = line.replace(f"{{{key}}}", str(val))
        return line
    return "Beta. Focus."

def get_volume(intervention_type: str) -> float:
    volumes = {
        "WARNING1": 0.60, "WARNING2": 0.70, "WARNING3": 0.80,
        "WARNING4": 0.90, "WARNING5": 1.00, "NUCLEAR": 1.00,
        "SNAPBACK_1": 0.60, "SNAPBACK_2": 0.65, "SNAPBACK_3": 0.65,
        "SNAPBACK_4": 0.65, "SNAPBACK_5": 0.65,
        "RESET_PRAISE": 0.70, "RADIO": 0.55,
        "BREAK_CHECKIN_15": 0.55, "BREAK_CHECKIN_30": 0.65,
    }
    return volumes.get(intervention_type, 0.70)

def get_snapback_type(warning_level: int) -> str:
    return f"SNAPBACK_{min(warning_level, 5)}"