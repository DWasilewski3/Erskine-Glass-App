# Erskine & Sons Glass Quote App

A local Windows app for quoting glass work. It replaces the old Excel workbook: pick a client, enter window sizes, and save or email a branded quote.

The app runs on your computer in a browser at [http://127.0.0.1:5000](http://127.0.0.1:5000). Quotes are stored in the `data` folder. Nothing is uploaded to the internet.

## 1. Install Python

You need **Python 3.10 or newer**.

1. Open [https://www.python.org/downloads/](https://www.python.org/downloads/).
2. Download the latest Windows installer.
3. Run it.
4. On the first screen, check **Add python.exe to PATH**.
5. Click **Install Now**.
6. Close and reopen any Command Prompt or PowerShell windows.

Check that it worked:

```powershell
python --version
```

You should see something like `Python 3.12.x`. If Windows opens the Microsoft Store instead, use **Start**, search for **Manage app execution aliases**, and turn off the `python.exe` aliases. Then try `python --version` again.

## 2. Install the app dependencies

Open PowerShell, go to the folder that contains `app.py` and `requirements.txt`, and install the Python packages:

```powershell
cd path\to\Erskine-Glass-App
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

That installs:

- **Flask** — the local web app
- **openpyxl** — Excel quotes
- **xhtml2pdf** — PDF quotes
- **Pillow** — logo images in PDFs

If `pip` is not found, use `python -m pip` as shown above.

## 3. Start the app

From the same project folder:

```powershell
python app.py
```

A browser window should open to [http://127.0.0.1:5000](http://127.0.0.1:5000). If it does not, open that address yourself.

Leave the PowerShell window open while you work. To stop the app, click that window and press `Ctrl+C`.

## 4. How to use it

### Quote a job

1. Open **Quote**.
2. Select a **client**, or click **Add client** and fill in name, phone, email, and address.
3. Set the date and optional job notes.
4. Enter line items: qty, width, height, thickness, glass type, grid, color, VERT, and HORI.
5. Click **Add line** for more windows. Totals update as you type.
6. Click **Save quote**. Files are written to that client’s folder under `data\quotes`.

Saved files include:

- `quote.pdf` — customer quote (with prices)
- `quote.xlsx` / `quote.csv` — spreadsheet copies
- `glass_needed.pdf` / `glass_needed.csv` — sizes and glass types, no prices

To reopen a job, choose the client, pick a past quote, and click **Load**.

### Email

- **Generate email** — opens a draft to the client with the quote PDF attached. The message is also copied to the clipboard.
- **Email manufacturer** — opens a draft to Trulite (`kbloink@trulite.com`) with the glass needed PDF attached.

Outlook should open the draft. The client needs an email address on file for **Generate email** to fill in **To**.

### Download without saving

Use **Download** for the quote PDF, Excel, or CSV. Use **Glass Needed PDF** or **Glass Needed CSV** for the no-price list.

### Settings

Open **Settings** to edit:

- Company name, phone, email, and website
- Prices for glass types and grids
- TFee, Factor, and Mup multipliers
- Color and VERT / HORI options
- The client list

Click **Save catalog** when you are done.

Pricing matches the old Excel workbook:

```text
SqFt = max(4, round up((width × height) / 144) × qty)
Total = SqFt × (glass price + grid price) × TFee × Factor × Mup
```

Blank glass type uses a glass price of **1**. Blank grid uses **0**. Color, VERT, and HORI are stored on the quote but do not change the price.

## 5. Next time

You do not need to reinstall Python or the packages. Open PowerShell in the project folder and run:

```powershell
python app.py
```
