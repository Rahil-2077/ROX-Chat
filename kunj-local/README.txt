KUNJ — LOCAL CHAT SERVER (WINDOWS)
====================================

Ye tera Kunj chat ab tere apne PC pe chalega, aur same WiFi pe jitne bhi
devices hain, sab isko ek hi URL se access kar payenge.

STEP 1 — Flask install karo
----------------------------
Command Prompt (cmd) ya PowerShell kholo, is folder mein jao:

    cd path\to\kunj-local

Phir ye chalao:

    pip install -r requirements.txt

Agar "pip nahi mila" bole, to try karo:

    python -m pip install -r requirements.txt


STEP 2 — Server start karo
----------------------------
Same terminal mein:

    python server.py

Ye terminal khula hi rehna chahiye jab tak chat chalu rakhni hai.
Isse band kiya (Ctrl+C ya window band) to chat sab devices pe band ho jayegi.

Agar Windows Firewall popup aaye "Allow access?" — allow karo, warna
doosre devices connect nahi ho payenge.


STEP 3 — Apna local IP address nikaalo
----------------------------------------
Same ya nayi Command Prompt window mein:

    ipconfig

"Wireless LAN adapter Wi-Fi" ke neeche "IPv4 Address" dhundo — kuch aisa
dikhega: 192.168.1.7 (exact numbers tere WiFi ke hisaab se alag honge)


STEP 4 — Sab connect karo
----------------------------
- Apne PC pe:        http://localhost:5000
- Doosre devices pe:  http://<wahi IPv4 address>:5000
  jaise:              http://192.168.1.7:5000

Zaroori: sab devices (phone/laptop) same WiFi network pe hone chahiye
jis pe tera PC hai. Mobile data pe nahi chalega.


WHAT'S NEW
----------
- OWNER MODERATION SYSTEM: agar tera account "owner" naam se hai, to kisi
  bhi user ki profile khol ke (online list ya DM se) uske upar teen action
  milte hain:
    🔇 Mute  — us user ka message bhejna (room + DM dono) band ho jaata hai
               chuni hui duration ke liye (15min/30min/2hr/24hr/1week);
               timer khatam hote hi khud wapas khul jaata hai
    👢 Kick  — us user ko site se turant nikaal diya jaata hai (login/guest
               dono blocked), ek countdown timer dikhta hai use, jo khatam
               hote hi khud wapas andar aa jaata hai
    🚫 Ban   — permanent block, seedha ek click mein (koi duration nahi
               poochta) — jab tak tu khud "Revoke" na daboye tab tak wapas
               nahi aa sakta. Banned user ko "You are banned due to
               violating site rules" screen dikhti hai.
  Har action ke baad agar wo user currently muted/kicked/banned hai, to
  wahi button "↩️ Revoke" mein badal jaata hai use wapas normal karne ke
  liye. Owner apni khud ki id ko moderate nahi kar sakta.
  Pehli baar koi action lete waqt owner password poochega (ek baar cache
  ho jaata hai us session ke liye, baar baar nahi poochega).

- MULTI-ACCOUNT DETECTION: owner jab kisi ki profile kholta hai, to niche
  "Other accounts (same device)" section mein wo saare naam dikhte hain
  jo usi browser/device se pehle use ho chuke hain (guest ya account,
  koi bhi). Ye ek simple device-fingerprint (browser mein stored random
  ID) par based hai — agar wahi banda alag browser/device use kare to
  wahan track nahi hoga, lekin same browser mein multiple naam try karne
  pe pakड़ा jaayega.

SETTING UP THE OWNER ACCOUNT
------------------------------
Owner powers are tied to the exact username "owner" (case-insensitive).
Just register/sign up normally with username "owner" and whatever
password you like — that account automatically gets moderation powers.
Keep that password safe since it's also used to authorize every
mute/kick/ban action.


WHAT'S NEW (older)
----------
- Guest logout hone ke kuch second baad, uska naam doosre users ki DM list
  se bhi apne aap hat jaata hai (pehle sirf messages delete hote the, DM
  list mein naam reh jaata tha jab tak koi refresh na kare). Agar koi is
  waqt us guest se chat khole baitha ho, to wo automatically main-room mein
  wapas chala jaayega.
- Guest jab "log out" dabata hai, uske saare DM conversations turant delete
  ho jaate hain — taaki agar koi naya banda usi guest naam se aaye to use
  purane guest ke private chats na dikhein. (Registered accounts ka data
  is se safe hai, unka kabhi delete nahi hota.)
- Guest users ka gender/age (jo unhone login pe set kiya tha) ab doosre
  users ki profile card mein dikhta hai — pehle sirf "Guests don't have a
  saved profile" dikhta tha
- Room banane ka option abhi ke liye band kar diya hai — sabko sirf ek
  default room "main-room✨" milega, jo login/guest-join ke turant baad
  khud khul jaata hai
- Online users ab ek ke niche ek (list format) dikhte hain, gender/age
  ke saath — kisi pe click karo to uski poori profile card khulegi
  (photo, gender, age, bio, aur seedha "Message" button DM shuru karne ke liye)
- DM list sidebar se hatakar top-right corner mein ek mail (✉️) icon mein
  shift kar di hai — usme unread messages ka red badge count dikhta hai,
  dropdown khol ke conversations dekh sakte ho
- PERMANENT DATA FIX: ab agar tu Render pe MONGO_URI environment variable
  set karta hai, to saara data (accounts, rooms, messages) ek free MongoDB
  Atlas database mein save hota hai — Render restart/sleep hone pe bhi data
  nahi udega. Agar MONGO_URI set nahi hai (jaise apne PC pe local chalate
  waqt), to purane tarike se data.json file mein hi save hoga — kuch alag
  se karna nahi padega local ke liye.
- App ka naam ab "ROX" hai (pehle Kunj tha)
- Sidebar ko hide/show karne ka hamburger (☰) button chat header mein — chhoti
  screens/phone pe chat dekhna ab aasan hai
- Registered users ab apni profile edit kar sakte hain — photo, bio, age, gender
  (Sidebar mein "edit profile" link, password confirm karke save hota hai)
- USERNAME kabhi change nahi hoga, na khud, na admin panel se recommend karte
- Guests apna gender/age sirf login karte waqt set kar sakte hain — login ke
  baad guest profile edit nahi kar sakte (koi edit option unhe dikhega hi nahi)
- Har user ka apna colored avatar (naam ka pehla letter, consistent color)
- Emoji picker (chat box ke bagal wala 🙂 button)
- Polished message bubbles — consecutive messages ek sath group hote hain


RENDER PE PERSISTENT DATA SETUP (zaroori, ek baar karna hai)
--------------------------------------------------------------
1. cloud.mongodb.com pe free M0 cluster banao (see chat instructions)
2. Database user + Network Access (0.0.0.0/0) allow karo
3. Connection string copy karo (mongodb+srv://... wala)
4. Render dashboard -> tera service -> Environment tab
5. Add Environment Variable: Key = MONGO_URI, Value = wahi connection string
   (password wale <password> ko apne actual password se replace karna mat
   bhoolna)
6. Save karo, Render khud redeploy karega
7. Deploy hone ke baad ab tera data restart/sleep hone pe bhi safe rahega


NOTES
-----
- Saara data (accounts, rooms, messages) is folder mein "data.json" naam
  ki file mein save hota hai. Server band karke wapas chalao to purana
  data waisa hi rahega.
- Jab tak tera PC on hai aur server chal raha hai, tab tak hi chat kaam
  karegi — ye ek proper hosted website nahi hai, sirf local network ke
  liye hai.
- Router restart hua to IP address badal sakta hai — phir se ipconfig
  check kar lena.
