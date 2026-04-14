# SCM Chatbot — Complete Dify Build Guide (Updated)

> Step-by-step guide based on official Dify documentation.
> Reference: https://docs.dify.ai

---

## Step 0: Knowledge Base Setup (Before Building the App)

Go to Knowledge in the top nav. Create a new Knowledge Base.

### Upload These 4 Files Only

1. `accounts-and-onboarding.md`
2. `deposits-withdrawals-fees.md`
3. `trading-products-and-execution.md`
4. `risk-and-margin.md`

Do NOT upload `_company-profile.md` or this guide.

### Chunk Settings

- Indexing mode: High Quality (uses embedding tokens but gives better retrieval)
- Chunking method: Custom
- Delimiter: `##`
- Max chunk length: 1,024 characters
- Chunk overlap: 50 characters
- Text pre-processing: "Replace consecutive spaces, newlines and tabs" checked
- Delete all URLs and email addresses: unchecked
- Summary Auto-Gen: unchecked
- Chunk using Q&A format: unchecked

### Embedding Model

Use whatever embedding model you have configured in System Settings > Model Providers. If you have a choice, prefer one with good multilingual support.

### Test Retrieval Before Building

After indexing completes, use the Knowledge Base's built-in "Recall Test" feature. Type test queries and verify the right chunks come back:
- "How do I open an account?" should return chunks from accounts doc
- "What are your fees?" should return chunks from deposits doc
- "Can I buy Sonatel?" should return chunks from trading doc
- "Is my money safe?" should return chunks from risk doc

If the wrong chunks are returned, adjust the score threshold before proceeding.

---

## Step 1: Create the Chatflow App

1. In Dify, click Create App (top-right).
2. Select "Create from Blank."
3. Choose Chatflow (not "Chatbot" or "Workflow" — Chatflow gives you the visual node editor with a conversation layer).
4. Name it "SCM Customer Support."
5. You will land in the Chatflow editor with a Start node already placed.

---

## Step 2: Configure the Start Node

Click on the Start node in the canvas. The Start node is the entry point — it receives the user's message every time they type in the chat.

### System Variables (automatic, no config needed)

The Start node automatically provides these system variables to all downstream nodes:
- `sys.query` — the user's current message text
- `sys.conversation_id` — unique ID for this conversation
- `sys.user_id` — the user's ID
- `sys.files` — any files the user uploaded

You do NOT need to add custom input fields for a chatbot. The user types freely in the chat box, and their message is captured as `sys.query` automatically.

### Opening Statement

The opening statement is NOT configured on the Start node. It is configured in the app-level Features panel:

1. Click the "Features" button in the top toolbar of the Chatflow editor.
2. Find "Opening Statement" or "Conversation Opener."
3. Enable it and enter:

```
Welcome to Sahel Capital Markets support. I can help you with:

1. Account & Verification — opening accounts, KYC, login issues
2. Deposits, Withdrawals & Fees — funding, withdrawing, charges
3. Buying or Selling Investments — equities, bonds, placing orders
4. My Portfolio, Dividends & Coupons — holdings, payments, performance
5. Risk & Safety — investment protection, diversification, currency risk

How can I help you today?
```

4. If the Features panel supports "Suggested Opening Questions" (starter questions shown as clickable buttons), add:
   - How do I open an account?
   - What shares can I buy?
   - What are your fees?
   - Is my money safe?

These appear as clickable buttons below the opening message.

---

## Step 3: Add the Question Classifier Node

1. Drag a Question Classifier node onto the canvas.
2. Connect the Start node's output to the Question Classifier input.

### Configuration

**Input variable:** Select `sys.query` (the user's message).

**Model:** Select your LLM. A faster/cheaper model is fine here (e.g., GPT-3.5 Turbo or Claude Haiku) since classification is simpler than answering.

**Instructions (optional but recommended):** Add this in the Instructions field to help the LLM handle edge cases:

```
You are classifying customer support queries for Sahel Capital Markets (SCM), a West African brokerage that offers equities and bonds only. No forex, no crypto, no CFDs, no options. Classify based on the user's primary intent. If the query could fit multiple categories, choose the most actionable one.
```

**Classes (5 total):**

Class 1 — Account & Verification
```
Questions about opening an SCM account, KYC verification, identity documents, Ghana Card, login problems, password reset, joint accounts, corporate accounts, demo accounts, personal information updates, multi-currency wallets, account types.
```

Class 2 — Deposits, Withdrawals & Fees
```
Questions about depositing money, withdrawing money, mobile money (MTN MoMo, Vodafone Cash, AirtelTigo), bank transfers, wire transfers, fees, commissions, charges, settlement periods, available balance, currency conversion fees, inactivity fees, cheque deposits, payment methods.
```

Class 3 — Buying or Selling Investments
```
Questions about buying or selling shares, equities, stocks, bonds, placing orders, market orders, limit orders, stop-loss orders, subscription windows, trading hours, specific companies (Sonatel, Zenith, Ecobank, Consolidated Bank Ghana, etc.), tickers, GSE, NSE, BRVM, bond menu, coupon rates, maturity dates.
```

Class 4 — Portfolio, Dividends & Coupons
```
Questions about existing holdings, portfolio value, dividend payments, coupon payments, ex-dividend dates, bond maturity, investment performance, unreceived dividends, missing coupon payments, portfolio drops.
```

Class 5 — Risk & Safety
```
Questions about investment risk, safety of funds, diversification, currency risk, liquidity risk, whether money is protected, CSD custody, segregated accounts, what happens if SCM closes, whether bonds are safe, market drops, delisting, leverage (SCM does not offer it), losing money.
```

### Downstream Connections

Each class output becomes a separate path. Connect ALL 5 class outputs to the SAME next node (the Knowledge Retrieval node). In Dify, you drag a connection from each class to the same target node.

---

## Step 4: Add the Knowledge Retrieval Node

1. Drag a Knowledge Retrieval node onto the canvas.
2. Connect all 5 Question Classifier class outputs to this single node.

### Configuration

**Query variable:** Select `sys.query` (the user's original message — NOT the classifier output).

**Knowledge bases:** Click "Add" and select the Knowledge Base you created in Step 0 (containing all 4 documents).

**Retrieval Settings (node-level):**

If you have a rerank model:
- Rerank method: Weighted Score (semantic 0.7 / keyword 0.3) or Rerank Model
- Top K: 5
- Score Threshold: 0.5

If you do NOT have a rerank model:
- The retrieval will use the settings from the Knowledge Base itself
- Top K: 5
- Score Threshold: 0.5

### Output

The node outputs a variable called `result` — this is an array (list) of retrieved document chunks, each containing content, metadata, and title fields.

---

## Step 5: Add the Code Node (Context Validator)

1. Drag a Code node onto the canvas.
2. Connect the Knowledge Retrieval node's output to this Code node.

### Why This Node Exists

The Knowledge Retrieval node returns a list that might be empty or contain low-quality results. This Code node converts the list into a single text string and checks whether there is meaningful content. Without this check, the LLM would receive empty context and hallucinate answers.

### Input Variables

Click the Input Variables section. Add one variable:
- Variable name: `context`
- Value: Select the Knowledge Retrieval node, then its `result` output

### Python Code

```python
def main(context: list) -> dict:
    if context and len(context) > 0:
        combined = "\n\n".join(
            item.get("content", "") if isinstance(item, dict) else str(item)
            for item in context
        )
        if len(combined.strip()) > 50:
            return {
                "has_context": True,
                "context_text": combined.strip()
            }
    return {
        "has_context": False,
        "context_text": ""
    }
```

### Output Variables

Add two output variables:
- `has_context` — Type: Boolean
- `context_text` — Type: String

IMPORTANT: The output variable names must exactly match the keys in the return dictionary.

---

## Step 6: Add the IF/ELSE Node

1. Drag an IF/ELSE node onto the canvas.
2. Connect the Code node's output to this IF/ELSE node.

### Condition

Click on the IF branch condition:
- Variable: Select the Code node's `has_context` output
- Operator: "is" (equals)
- Value: `true`

The ELSE branch handles everything else (no context found).

### Downstream Connections

- IF (true) branch → connects to the Primary LLM node (Step 7)
- ELSE branch → connects to the Fallback LLM node (Step 8)

---

## Step 7: Add the Primary LLM Node

1. Drag an LLM node onto the canvas.
2. Connect the IF (true) branch to this node.

### Model Settings

- Model: Your chosen LLM (e.g., GPT-4o, Claude Sonnet)
- Temperature: 0 (use the "Precise" preset if available)
- Max tokens: 1024

### Context (IMPORTANT — Dify-specific feature)

The LLM node has a dedicated "Context" field separate from the prompt. This is the correct way to pass Knowledge Retrieval results in Dify:

However, since we processed the retrieval results through the Code node into a string, we will pass `context_text` as a variable in the prompt instead. If you want to use Dify's built-in citation feature, you can ALSO add the original Knowledge Retrieval `result` to the Context field — this enables the citation UI without affecting the prompt.

### System Prompt

In the SYSTEM message box, enter the following. Use the `/` key or `{{` to insert variables where indicated:

```
You are a customer support assistant for Sahel Capital Markets (SCM), a licensed West African brokerage headquartered in Accra, Ghana with offices in Lagos and Abidjan. SCM offers 20 selected equities across the Ghana Stock Exchange (GSE), Nigerian Stock Exchange (NSE), and Bourse Regionale (BRVM), plus a curated menu of sovereign and corporate bonds.

RULES — follow these strictly:

1. Answer ONLY based on the context provided below. Do not use any outside knowledge. If the context does not contain enough information to answer, say "I don't have specific information on that. Let me connect you with our team" and suggest the appropriate contact from the list below.

2. Never provide personal investment advice such as "you should buy X" or "I recommend Y." If asked, respond: "SCM cannot provide personal investment advice. For market analysis and sector insights, I recommend reading the weekly West Africa Market Pulse report from Dr. Nana Adjei, our Head of Research."

3. Never predict prices, returns, or market movements.

4. When the context mentions escalating to a specific team member, always include their full name and role. Then list what information the user should prepare before the handoff.

5. Use GHS as the default currency and GMT as the default timezone unless the user's question is specifically about an NSE instrument (use NGN/WAT) or BRVM instrument (use XOF/GMT).

6. Keep answers concise, direct, and professional. Do not repeat the user's question back to them.

7. If the user asks about a product or service that SCM does not offer (forex, CFDs, options, cryptocurrency, margin trading, leverage), respond clearly: "SCM does not offer [product]. SCM specialises in West African equities and bonds."

TEAM CONTACTS — use these when escalation is needed:
- Abena Owusu, KYC Officer: verification failures, document issues, name changes
- Ama Mensah, Head of Client Relations (Accra): general account issues, login problems
- Chidi Okonkwo, Client Relations Manager (Lagos): Nigerian market client issues
- Marie Kouassi, Client Relations Associate (Abidjan): BRVM queries, Francophone support
- Yaw Boateng, Head Trader: equity execution disputes, order fill issues, price feed errors
- Fatima Diallo, Bond Desk Manager: bond subscriptions, coupon payments, bond availability
- Dr. Nana Adjei, Head of Research: market analysis, research reports, product information
- Tunde Bakare, Equity Research Analyst: banking and telecoms sector analysis
- Emeka Nwosu, Head of Compliance: regulatory matters, large withdrawals, custodial safety
- Kofi Mensah, Operations Manager: deposits, withdrawals, settlement, fee disputes

CONTEXT:
{{context_text}}
```

To insert `{{context_text}}`, type `/` in the prompt editor, then select the Code node's `context_text` output variable.

### User Prompt

In the USER message box:
```
{{sys.query}}
```

Type `/` and select `sys.query` from the system variables.

### Memory

Enable "Memory" on this LLM node. This gives the LLM access to previous messages in the conversation so it can handle follow-up questions like "what about bonds?" after asking about equities. Set the memory window to the last 10 messages.

---

## Step 8: Add the Fallback LLM Node

1. Drag another LLM node onto the canvas.
2. Connect the ELSE branch from the IF/ELSE node to this node.

### Model Settings

- Model: Same as primary LLM (or a cheaper/faster one since this is just a polite deflection)
- Temperature: 0
- Max tokens: 512

### System Prompt

```
You are a customer support assistant for Sahel Capital Markets (SCM). The knowledge base did not return relevant information for the user's query.

RULES:
1. Do NOT guess or make up any information about SCM's products, fees, processes, or team.
2. Acknowledge that you cannot answer this specific question.
3. Suggest the most relevant team contact based on the topic:
   - Account issues: Ama Mensah (Head of Client Relations, Accra) or Chidi Okonkwo (Client Relations Manager, Lagos)
   - Deposit/withdrawal/fee issues: Kofi Mensah (Operations Manager)
   - Trading/order issues: Yaw Boateng (Head Trader)
   - Bond questions: Fatima Diallo (Bond Desk Manager)
   - Risk/safety questions: Emeka Nwosu (Head of Compliance)
   - General/research: Dr. Nana Adjei (Head of Research)
4. Ask if the user would like help with something else.

Respond in this format:
"I don't have enough information to answer that specifically. For [topic], I'd recommend reaching out to [Name] ([Role]) who can assist you directly. Is there anything else I can help you with?"
```

### User Prompt

```
{{sys.query}}
```

### Memory

Enable Memory here too (same settings as primary LLM).

---

## Step 9: Add Answer Nodes

In Dify Chatflow, the Answer node is what sends text back to the user in the chat. You need TWO Answer nodes — one for each branch.

### Answer Node A (after Primary LLM)

1. Drag an Answer node onto the canvas.
2. Connect the Primary LLM node's output to this Answer node.
3. In the Answer node content, type `/` and select the Primary LLM node's `text` output.

The content should just be: `{{primary_llm.text}}` (the exact variable reference depends on your node name — use `/` to select it).

### Answer Node B (after Fallback LLM)

1. Drag another Answer node onto the canvas.
2. Connect the Fallback LLM node's output to this Answer node.
3. In the Answer node content, reference the Fallback LLM node's `text` output.

Note: Dify Chatflow supports multiple Answer nodes. Each one can deliver content at different points in the flow.

---

## Complete Node Flow

```
┌──────────────────┐
│   START           │  Provides sys.query automatically
│                   │  Opening statement set in Features panel
└────────┬─────────┘
         │
         v
┌──────────────────┐
│   QUESTION        │  Input: sys.query
│   CLASSIFIER      │  Model: GPT-3.5 Turbo or similar
│   (5 classes)     │  5 classes with descriptions
└──┬──┬──┬──┬──┬───┘
   │  │  │  │  │
   C1 C2 C3 C4 C5   (all connect to same next node)
   │  │  │  │  │
   └──┴──┴──┴──┘
         │
         v
┌──────────────────┐
│   KNOWLEDGE       │  Query: sys.query
│   RETRIEVAL       │  Source: all 4 docs
│                   │  Top-K: 5, Threshold: 0.5
│                   │  Output: result (list of chunks)
└────────┬─────────┘
         │
         v
┌──────────────────┐
│   CODE            │  Input: context = KR.result
│   (Python)        │  Converts list → string
│                   │  Checks if content exists
│                   │  Output: has_context, context_text
└────────┬─────────┘
         │
         v
┌──────────────────┐
│   IF / ELSE       │  IF: has_context == true
│                   │  ELSE: fallback path
└───┬──────────┬───┘
    │          │
   TRUE      FALSE
    │          │
    v          v
┌────────┐ ┌────────┐
│PRIMARY │ │FALLBACK│  Both have Memory enabled
│  LLM   │ │  LLM   │  Both use temperature 0
│        │ │        │
└───┬────┘ └───┬────┘
    │          │
    v          v
┌────────┐ ┌────────┐
│ANSWER  │ │ANSWER  │  Each references its LLM's text output
│  (A)   │ │  (B)   │
└────────┘ └────────┘
```

Total: 8 nodes (Start, Question Classifier, Knowledge Retrieval, Code, IF/ELSE, Primary LLM, Fallback LLM, 2x Answer = 8 placed nodes).

---

## Step 10: App-Level Features

Click the "Features" button in the top toolbar to configure these:

### Opening Statement
Already configured in Step 2.

### Suggested Questions After Answer
Enable this. After the bot answers, it will suggest follow-up questions as clickable buttons. This keeps users engaged and within the knowledge base scope.

### Citation and Attribution
Enable this. When the LLM node has a Context field connected to a Knowledge Retrieval result, Dify automatically shows which knowledge chunk the answer was sourced from. This builds user trust.

To enable citations: In the Primary LLM node (Step 7), add the Knowledge Retrieval node's `result` variable to the LLM's Context field (separate from the prompt). This is in addition to passing `context_text` in the system prompt.

### Content Moderation
If available, enable input moderation to block profanity, abuse, and prompt injection attempts.

### Text to Speech / Speech to Text
Off unless needed.

---

## Step 11: Preview and Test

1. Click "Preview" in the top-right of the Chatflow editor.
2. The chat interface appears on the right side.
3. Run through the test cases below.

### Should return confident answers

| Query | Expected Source | Key Points |
|-------|----------------|------------|
| "How do I open an account?" | accounts doc | SCM Invest app, GHS 500 minimum, KYC steps |
| "What shares can I buy?" | trading doc | 20 equities, 6 sectors, GSE/NSE/BRVM |
| "Can I buy Sonatel?" | trading doc | Yes, SNTS, BRVM, XOF, 1.0% conversion fee |
| "How do bonds work?" | trading doc | Face value, coupon, maturity, 0.5% fee |
| "What are your fees?" | deposits doc | 1.5% equity, 0.5% bond, no inactivity |
| "My MoMo deposit is missing" | deposits doc | Check transaction ID, Kofi Mensah escalation |
| "Is my money safe?" | risk doc | Segregated accounts, CSD, SEC Ghana |
| "KYC rejected twice" | accounts doc | Escalate to Abena Owusu |
| "What are the trading hours?" | trading doc | GSE/NSE/BRVM specific hours |
| "How do I diversify?" | risk doc | Sectors, exchanges, currencies, equities+bonds |

### Should trigger refusal

| Query | Expected |
|-------|----------|
| "Should I buy Zenith?" | Refuse advice, suggest Market Pulse report |
| "Do you offer forex?" | "SCM does not offer forex..." |
| "Can I trade crypto?" | "SCM does not offer cryptocurrency." |
| "What will gold do?" | Refuse to predict |
| "Weather in Accra?" | Fallback — suggest team contact |

### Should include escalation contact

| Query | Expected Contact |
|-------|-----------------|
| "Withdrawal stuck for a week" | Kofi Mensah (Operations) |
| "Bond coupon is late" | Fatima Diallo (Bond Desk) |
| "Order at wrong price" | Yaw Boateng (Head Trader) |
| "Is my account hacked?" | Ama Mensah + Emeka Nwosu |

---

## Step 12: Publish

Once testing passes:
1. Click "Publish" in the top-right.
2. Choose your deployment method:
   - Embed in website (iframe or script tag)
   - Share via URL
   - Access via API

---

## Step 13: Post-Launch Tuning

### Week 1: Retrieval Quality

Go to Logs in the app dashboard:
- Check which chunks were retrieved for each query (visible in citation data).
- If wrong chunks appear: raise score threshold (0.5 → 0.55 → 0.6).
- If good chunks are missed: lower threshold (0.5 → 0.45).
- If too few results: increase Top-K (5 → 7).

### Week 2: Answer Quality

- Answers too long? Add "Keep answers under 150 words" to the system prompt.
- Answers too vague? Increase Top-K to give the LLM more context.
- Hallucinating? Confirm temperature is 0. Reinforce "ONLY based on context" in prompt.

### Ongoing

- Repeated unanswerable questions → add new sections to the relevant .md file, re-upload to knowledge base.
- Misrouted queries → update Question Classifier class descriptions.
- French-speaking users → consider adding Marie Kouassi as default contact for unclassified queries, or add French content to the knowledge base.

---

## Common Mistakes to Avoid

1. Do NOT upload `_company-profile.md` to the knowledge base.
2. Do NOT set temperature above 0 for a support chatbot.
3. Do NOT skip the Code node — without it, empty retrieval results cause hallucination.
4. Do NOT put the opening statement in the Start node — it goes in the Features panel.
5. Do NOT use the LLM node's Context field as the ONLY way to pass retrieved text — also include it in the system prompt via the Code node's `context_text` variable for reliable grounding.
6. Do NOT forget to enable Memory on LLM nodes — without it, follow-up questions like "what about bonds?" won't work.
7. Do NOT set Top-K above 8 — too many chunks dilute relevant context with noise.
8. Do NOT set score threshold above 0.7 initially — start at 0.5 and tune upward.
9. Do NOT forget to test the "no context" path — send an irrelevant query and verify the fallback LLM responds gracefully.
