# 🛡️ Fraud Alert Voice Agent — Day 6 (Murf AI Voice Agents Challenge)

A real-time **Fraud Detection Voice Agent** built using  
**LiveKit Agents + Gemini + Deepgram STT + Murf Falcon TTS**, capable of:

✔️ Verifying customer identity  
✔️ Reading suspicious transaction alerts  
✔️ Asking for confirmation (“Did you make this transaction?”)  
✔️ Marking a case as *legitimate* or *fraudulent*  
✔️ Updating a JSON-based fraud database  
✔️ Speaking naturally in a human-like voice  

This project is part of **Day 6** of the  
_**Murf AI Voice Agents Challenge — #10DaysofAIVoiceAgents**_.

---

## 🚀 Features

### 🔹 1. Customer Identity Verification  
- User provides their name  
- Agent loads fraud case from JSON database  
- User confirms their *Security Identifier*  
- Incorrect verification → call stops safely

### 🔹 2. Suspicious Transaction Review  
Agent reads:
- Amount  
- Merchant  
- Time  
- Source  
- Card ending  

### 🔹 3. Yes/No Confirmation  
- “YES” → Case is marked as **confirmed_safe**  
- “NO” → Case is marked as **confirmed_fraud**  
- Updates values inside `fraud_db.json`

### 🔹 4. Natural AI Voice  
- Powered by **Murf Falcon** text-to-speech  
- Smooth, real-time speech  
- Conversational tone

---

