![Welcome Banner](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExaTVybGR6cmZubjg2ZDd4cm53bWFubzV4b3NpemQ2ZjZzaTMxMTdzbiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/3o7abAHdYvZdBNnGZq/giphy.gif)

# Hey there! I'm Yasin 👋

**A backend developer, bot-maker, Linux lover, curious mind who tries to learn EVERYTHING.**

---

### ✨ About Me

- 🔭 Currently Working On: building bots, backend systems, and automation scripts.
- 🌱 Currently Learning: *everything that sounds cool* – from Telegram bots to server security, databases, Rubika platform, and more.
- 👨‍💻 I love writing "Silence Mode" logic for bots — so they can work quietly like ninjas 🤫🤖
- 💡 My repos basically show my journey of learning: Django projects, Laravel apps, API experiments, bot engines, Linux setup scripts, and random stuff!!
- ⚡ Fun Fact: I break things just to fix them again 😅  

> I’m not a “one language only” dev.  
> I love to experiment with Python, JavaScript, PHP, Bash, bug-hunting in Linux, anything that makes my brain happy.

---

### 🚀 My Tech Stack

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/-Django-092E20?logo=django&logoColor=white)
![Laravel](https://img.shields.io/badge/-Laravel-f34e2e?logo=laravel&logoColor=white)
![Telethon](https://img.shields.io/badge/-Telethon-green?logo=telegram)
![Bash](https://img.shields.io/badge/-Bash-4EAA25?logo=gnubash&logoColor=white)
![Linux](https://img.shields.io/badge/-Linux-FCC624?logo=linux&logoColor=black)
![JavaScript](https://img.shields.io/badge/-JavaScript-F7DF1E?logo=javascript&logoColor=black)
![PHP](https://img.shields.io/badge/-PHP-777BB4?logo=php&logoColor=black)
![Docker](https://img.shields.io/badge/-Docker-2496ED?logo=docker&logoColor=white)

---

### 🤖 Silence Mode Coding (New!)

I recently added a new **Silence Mode** approach in my bot projects for Telegram and Rubika (a Persian social platform).  
This feature makes bots do their job *without sending notifications or noise* — perfect for night-time tasks or quiet groups!

```python
# Simple example for enabling silence mode:
class MyBot:
    def __init__(self):
        self.silence = False

    def enable_silence(self):
        self.silence = True

    def handle(self, msg):
        if self.silence:
            # Handle quietly
            print("🔇 Silent handling...")
        else:
            print("Normal reply")