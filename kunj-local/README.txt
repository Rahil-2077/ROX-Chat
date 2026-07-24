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
- "Online now" strip sidebar mein — dekh sakta hai kaun abhi active hai
- DM list mein green/grey dot — friend online hai ya nahi
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
