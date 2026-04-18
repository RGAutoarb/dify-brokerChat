# SCM Customer Bilingual Chatbot — Setup & Deployment

## Overview

`SCM Customer Bilingual.yml` is a French-default, English-capable chatbot that serves Sahel Capital Markets customers in both languages. Users can switch between French and English mid-conversation by typing keywords or requests in either language.

---

## Setup: 3 Steps

### 1. Get Your French Knowledge Base Dataset ID

1. Open Dify Dashboard → **Knowledge**
2. Find the **`demo3_fr`** knowledge base (the French translations)
3. Click it → **Settings** (⚙️ icon)
4. Look for the **Dataset ID** field → Copy it (looks like: `wpiX2IGTHuNIgBsNQH+FQDH7Eg+y3+n04...`)

### 2. Edit the YAML File

1. Open `/home/rossg/source/Leonce/dify/docs/brokerage-demo2/SCM Customer Bilingual.yml` in a text editor
2. Search for the string: `FRENCH_KB_DATASET_ID_HERE`
3. Replace it with the dataset ID you copied in Step 1
4. Save the file

**Example:**
```yaml
# BEFORE:
dataset_ids:
- wpiX2IGTHuNIgBsNQH+FQDH7Eg+y3+n04wvbypJdQxp9DfhtoUOy49poWV7bGtnr
- FRENCH_KB_DATASET_ID_HERE

# AFTER:
dataset_ids:
- wpiX2IGTHuNIgBsNQH+FQDH7Eg+y3+n04wvbypJdQxp9DfhtoUOy49poWV7bGtnr
- abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

### 3. Import into Dify

1. Open Dify Dashboard → **Apps** (or Studio)
2. Click **+ New App** or **Import**
3. Choose **Import from File**
4. Select `SCM Customer Bilingual.yml`
5. Click **Confirm** → The app will be imported with both knowledge bases linked

---

## Testing

### Test 1: French Default
- Start a **new conversation**
- You should see a **bilingual welcome** message (French first, then English note)
- Ask in French: `"Quels sont vos frais?"` (What are your fees?)
- Bot responds entirely in French

### Test 2: Language Switch
- In the same conversation, type: `"English please"` or just `"English"`
- Bot responds: 🇬🇧 **Language switched to English**
- Ask: `"What are your fees?"`
- Bot responds entirely in English

### Test 3: Switch Back
- Type: `"Français"` or `"français"`
- Bot confirms: 🇫🇷 **Langue changée en français**
- Ask: `"Quels documents ai-je besoin pour KYC?"`
- Bot responds in French

### Test 4: Knowledge Retrieval
Verify both knowledge bases are being queried:
- Ask in French: `"Comment ouvrir un compte?"` — should cite French KB content
- Ask in English: `"How do I open an account?"` — should cite English KB content

---

## Architecture at a Glance

```
User Input
    ↓
Language Detector (detects "english", "français", etc.)
    ↓
Language Assigner (saves lang choice to conversation.lang)
    ↓
Language Switch? Yes → Confirmation ("🇫🇷 Langue changée..." or "🇬🇧 Language switched...")
           ↓ No
Question Classifier (6 categories: Account, Deposits, Trading, Portfolio, Risk, Off-Topic)
    ↓
Knowledge Retrieval (searches BOTH English + French KBs)
    ↓
LLM System Prompt: "Current language is {{#conversation.lang#}} — respond in that language only"
    ↓
Primary LLM (if context found) OR Fallback LLM (no context)
    ↓
Answer (in the selected language)
```

---

## Key Features

| Feature | Implementation |
|---------|---|
| **Default Language** | French (`conversation.lang` defaults to `"fr"`) |
| **Language Switching** | Type keywords: "english", "en", "anglais", "français", "fr" — mid-conversation, anytime |
| **Knowledge Bases** | Both English + French KBs queried simultaneously; LLM selects language-appropriate chunks |
| **Question Classifier** | Updated with French category descriptions for reliable routing in French |
| **LLM Prompts** | Primary and Fallback LLMs have explicit language instructions: "If lang=fr, respond entirely in French..." |
| **Team Contacts** | Bilingual: each role listed in French and English (e.g., "KYC Officer / Responsable KYC") |
| **Opening Statement** | Bilingual welcome with instructions: "Langue / Language" switching available |
| **Suggested Questions** | 4 French questions matching the English originals |

---

## Conversation Variable: `lang`

The `lang` conversation variable **persists across turns in the same conversation**:
- Initialized to `"fr"` (French)
- Updated when user types language switch keywords
- Remembered for the entire session
- Each new conversation resets to French

---

## Debugging

### Problem: Bot keeps responding in English even after I switched to French
**Solution:** Make sure you typed a keyword the `lang_selector_node` recognizes:
- For French: `"français"`, `"francais"`, `"french"`, `"fr"`, `"en français"`
- For English: `"english"`, `"anglais"`, `"en"`, `"in english"`

### Problem: French answers don't cite the knowledge base
**Solution:** Verify the French KB dataset ID was correctly substituted in Step 2. Check:
```bash
grep "FRENCH_KB_DATASET_ID_HERE" /home/rossg/source/Leonce/dify/docs/brokerage-demo2/SCM\ Customer\ Bilingual.yml
```
If that string still appears, it wasn't replaced.

### Problem: Opening statement not bilingual
**Solution:** Confirm the YAML was imported correctly and the `opening_statement` in the features section starts with French text.

### Problem: Classifier not routing French queries correctly
**Solution:** The `qc_node` has been updated with French class descriptions. If it's still routing wrong, re-import the YAML file.

---

## Customization

### To Add More Language Switch Keywords
Edit the `lang_selector_node` (code node) → modify the `switch_to_fr` and `switch_to_en` lists with additional keywords.

### To Change the Default Language
Find the `conversation_variables` section and change `value: fr` to `value: en` (or any other language code).

### To Add a Third Language (e.g., Spanish)
1. Create a Spanish knowledge base in Dify
2. Add its dataset ID to the `kr_node`
3. Add language detection logic to `lang_selector_node` for Spanish keywords
4. Update LLM prompts to handle Spanish

---

## Files Involved

| File | Purpose |
|---|---|
| `SCM Customer Bilingual.yml` | The complete chatbot workflow (this is what you import into Dify) |
| `demo3_fr` (Knowledge Base) | French translations of all SCM knowledge documents |
| `WALKTHROUGH.md` | Original English chatbot setup guide (still applies, swap YAML filename) |
| `accounts-and-onboarding-fr.md` | French knowledge source used in `demo3_fr` |
| `deposits-withdrawals-fees-fr.md` | French knowledge source |
| `risk-and-margin-fr.md` | French knowledge source |
| `trading-products-and-execution-fr.md` | French knowledge source |

---

## Support

For questions about Dify workflows, knowledge base setup, or testing:
1. Check `WALKTHROUGH.md` — most of it still applies (just use the new YAML)
2. Run evaluation tests: `python scripts/stress-test/eval/run_eval.py ...` (tests work for both languages if you set up queries in both)
3. Inspect the workflow graph in Dify Studio to visually trace the new language-switching nodes

---

**Last updated:** April 16, 2026  
**YAML version:** 0.6.0  
**Chatbot name:** SCM Customer Bilingual  
**Default language:** French 🇫🇷
