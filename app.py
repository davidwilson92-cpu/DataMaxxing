from fastapi.responses import PlainTextResponse

from nova.app import app


@app.get(
    "/tiktokudskSXJARxjy3dT8df559aYaiaRJmZJe.txt",
    response_class=PlainTextResponse,
    include_in_schema=False,
)
def tiktok_site_verification() -> PlainTextResponse:
    return PlainTextResponse(
        "tiktok-developers-site-verification=udskSXJARxjy3dT8df559aYaiaRJmZJe"
    )
