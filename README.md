# ChatGPT → X Poster

This wraps the existing Tweepy posting logic in a private HTTPS API that a Custom GPT Action can call.

## What changes

Current flow: GitHub Actions → `post_tweet.py` → X.

New flow: Custom GPT → secured API → X.

The GitHub Action can remain as a backup.

## 1. Add these files to the existing GitHub repository

Copy all files in this folder into the repository root. Keep the existing `post_tweet.py` and workflow.

Commit and push.

## 2. Deploy on Render

1. Create a Render account and choose **New → Blueprint**.
2. Connect the GitHub repository.
3. Render will detect `render.yaml`.
4. Enter the four existing X credentials when prompted:
   - `X_API_KEY`
   - `X_API_SECRET`
   - `X_ACCESS_TOKEN`
   - `X_ACCESS_TOKEN_SECRET`
5. Confirm `X_USERNAME=DataMaxxing` or replace it with the correct handle.
6. Deploy.

Render generates `POSTING_API_KEY`. Open the service's Environment page and securely copy its value; it is the key entered into the GPT Action authentication screen.

The deployed service URL will resemble:

`https://x-chatgpt-poster.onrender.com`

Test health in a browser:

`https://YOUR-SERVICE.onrender.com/health`

Expected response:

```json
{"status":"ok"}
```

## 3. Test the private endpoint

Replace the placeholders:

```bash
curl -X POST "https://YOUR-SERVICE.onrender.com/x/preview" \
  -H "Authorization: Bearer YOUR_POSTING_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing the private X API","approved":false}'
```

For one deliberate live test:

```bash
curl -X POST "https://YOUR-SERVICE.onrender.com/x/post" \
  -H "Authorization: Bearer YOUR_POSTING_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text":"Testing my ChatGPT to X integration.","approved":true}'
```

That second command publishes a real post.

## 4. Create the Custom GPT

1. In ChatGPT on the web, open **GPTs → Create**.
2. Under **Configure**, paste `custom-gpt-instructions.txt` into Instructions.
3. Open **Actions → Create new action**.
4. Open `openapi-action.yaml` and replace the server URL with the deployed Render URL.
5. Paste the complete schema into the Action editor.
6. Set Authentication to:
   - Type: **API key**
   - Auth type: **Bearer**
   - API key: the value of `POSTING_API_KEY`
7. Test `previewXPost` first.
8. Keep the GPT private and save it.

## 5. Use it

Example:

1. “Draft a post about AWS growth in the DataMaxxing style.”
2. “Make it shorter.”
3. “Post it.”

The publish endpoint requires both valid bearer authentication and `approved=true`. The GPT instructions also prohibit publishing until the exact final wording has been explicitly approved.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Export the variables from .env, then:
uvicorn app:app --reload
```

Run tests:

```bash
pip install pytest httpx
pytest -q
```

## Security notes

- Never commit `.env` or any credentials.
- Keep the GPT private.
- Use a long, random `POSTING_API_KEY` unrelated to the X credentials.
- Rotate `POSTING_API_KEY` immediately if it is exposed.
- The endpoint currently publishes text-only posts. The original CLI still supports local image uploads; adding images to the web workflow requires a separate upload/storage design.
