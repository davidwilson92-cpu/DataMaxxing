# Zova Meta review package

## Product use case

Zova is an AI social manager for content creators. A creator connects their own Instagram Professional account, gives Zova one idea, receives an Instagram-native draft, reviews it, and explicitly chooses when to publish. Zova also reads the creator's recent captions to learn their writing style.

## Permissions requested

### instagram_business_basic

Zova uses this permission to identify the creator's connected professional account and read recent profile content. Recent captions are used to create the creator's private voice profile and display account activity inside their authenticated Zova workspace.

### instagram_business_content_publish

Zova uses this permission only after the creator reviews a generated draft and selects Review and publish. Zova uploads the creator-selected image or video with the approved caption to the creator's own Instagram account.

## Reviewer journey

1. Open `https://YOUR-DOMAIN/signup` and create the supplied reviewer account.
2. On Connect your socials, select Connect beside Instagram.
3. Sign in with the supplied Instagram Professional test account and approve access.
4. Confirm that Instagram is shown as connected and recent content is reflected in the creator workspace.
5. In Studio, enter a short idea, choose Instagram, add a test image, and select Shape for every platform.
6. Review the generated caption, choose Review and publish, and confirm publication.
7. Open Account and select Unlink beside Instagram.

## Screencast checklist

- Show the Zova domain and reviewer login.
- Show Instagram authorization and requested permissions.
- Show the connected Instagram username in Zova.
- Show recent content and voice learning.
- Show a draft generated from one idea.
- Show the creator reviewing and publishing an image or video.
- Show the resulting Instagram post.
- Show Unlink and the public data-deletion page.

## Required public URLs

- Privacy: `https://YOUR-DOMAIN/privacy-policy`
- Terms: `https://YOUR-DOMAIN/terms-of-service`
- Data deletion instructions: `https://YOUR-DOMAIN/data-deletion`
- Data deletion callback: `https://YOUR-DOMAIN/data-deletion/callback`

Replace every `YOUR-DOMAIN` before submission. Give Meta a dedicated reviewer account and an Instagram Professional test account. Do not request permissions that are not demonstrated in the screencast.
