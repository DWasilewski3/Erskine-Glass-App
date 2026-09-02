# How to use the Erskine Glass Quote App

This guide is for day-to-day quoting. For first-time install, see `README.md`.

Start the app from the project folder:

```powershell
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000). Leave the PowerShell window open while you work.

---

## Quote a job

1. On the **Quote** page, pick a **client**, or click **Add client** and enter name, phone, email, and address.
2. Set the date. Add job notes if you want them on the quote and in the email.
3. Enter each window:
   - **Qty**, **Width**, **Height**, **Thick**, **Type**, **Grid**, **Color**, **VERT**, **HORI**
   - Width and height are inches plus 16ths. Type `22 1/16`, or enter `22` and pick `1/16` from the list.
4. Click **Add line** for more windows. Qty, SqFt, and Total update as you type.
5. Click **Save quote**. Files go in that client’s folder under `data\quotes`.

Saved files:

- `quote.pdf` — customer quote with prices
- `quote.xlsx` / `quote.csv` — spreadsheet copies
- `glass_needed.pdf` / `glass_needed.csv` — sizes and glass types, no prices

To reopen a job, choose the client, pick a past quote, and click **Load**.

**Clear** starts a blank quote. It does not delete saved files.

---

## Download files without saving

Use **Download** for the quote PDF, Excel, or CSV. Use **Glass Needed PDF** or **Glass Needed CSV** for the no-price list.

---

## Email a client or the manufacturer

If a Resend API key is saved in **Settings**, the app sends the email for you from `erskineson@erskineson.com`. The quote PDF (or glass needed PDF) is attached.

If no key is set, or Resend cannot send, the app falls back to clipboard history so you can paste the message in your own email.

### Set up Resend (one-time)

1. Create an API key at [resend.com/api-keys](https://resend.com/api-keys).
2. Verify the `erskineson.com` domain in Resend (**Domains**).
3. Open this app’s **Settings** page.
4. Paste the key into **Resend integration** and click **Save API key**.
5. The key is stored only in a local `.env` file on this computer, not in the catalog.

### Generate email (client)

1. Select the client. They need an email address on file.
2. Click **Generate email**.
3. If Resend is connected, the status line will say the email was sent.
4. If Resend is not connected, the quote PDF downloads and To / subject / body are copied for **Windows + V**.

### Email manufacturer

Same steps, but click **Email manufacturer**. That sends (or copies) the Trulite address (`kbloink@trulite.com`), a “Glass needed” subject, and the manufacturer message, with the **glass needed PDF** attached.

### Turn on Windows clipboard history (one-time, fallback)

**Windows + V** opens clipboard history. The first time, click **Turn on**. After that, Windows keeps several recent copies so you can paste To, subject, and body one at a time.

### Using Windows + V

| Key | What it does |
| --- | --- |
| **Windows + V** | Opens clipboard history (a list of recent copies) |
| Click an item | Pastes that item |
| Pin an item | Keeps it in the list after newer copies |

Tips:

- If **Windows + V** does nothing useful, open it once and click **Turn on**.
- Copy order is To, then subject, then body. Body is usually the top (newest) item.
- If a field already has old text, select that text first, then paste.
- The PDF is a downloaded file, not a clipboard item. Attach it with your email’s **Attach** button (often in Downloads).

---

## Settings

Open **Settings** to edit:

- Company name, phone, email, and website
- Glass type and grid prices
- TFee, Factor, and Mup
- Colors and VERT / HORI options
- The Resend API key (use **Save API key**)
- The client list

Click **Save catalog** when you are done with prices and clients. Save the Resend key with its own button.

---

## Pricing

```text
SqFt = max(4, round up((width × height) / 144) × qty)
Total = SqFt × (glass price + grid price) × TFee × Factor × Mup
```

Blank glass type uses a glass price of **1**. Blank grid uses **0**. Color, VERT, and HORI do not change the price.
