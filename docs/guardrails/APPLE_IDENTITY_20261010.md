# Apple hybrid-flow identity validation

Candidate only; full local/PostgreSQL validation pending. Production unchanged.

Signed synthetic-token regressions reproduced acceptance of a front-channel
identity token without expiry, and acceptance when the token exchange returned a
different subject, nonce or expired identity. Previous account tests mocked JWT
decoding and did not provide evidence for these cryptographic checks.

The callback now validates the front-channel token before exchanging its code.
The Apple profile requires RS256 signatures, the fixed issuer, exact scalar client
audience, expiry, issued-at, nonempty subject and the stored nonce. If present,
authorized-party must match the client. Claim types are checked. Hybrid-flow
`c_hash` must match the authorization code using the left half of SHA-256,
base64url without padding. Only then is the code sent to Apple's fixed endpoint.

The exchange must return HTTP 200 and a JSON identity token. That token receives
the same signature/issuer/audience/expiry/nonce checks, and issuer, subject,
audience and nonce must match the front-channel identity before account lookup or
mutation. Exchange identity tokens need not contain `c_hash`. Keys use a bounded
network timeout; provider transport and malformed-response failures return generic
errors. Consumed state remains consumed, with no automatic exchange retry. No
provider tokens, diagnostic details or signing material are stored by these tests.

Tests use a generated RSA key and real PyJWT verification, with mocked public-key
retrieval and token exchange. They cover omitted claims, wrong signatures, code
hashes, issuer/audience/authorized-party, nonce, expiry/issued-at, malformed claim
types, mismatched exchange identities, malformed JSON, missing exchange token,
provider rejection, timeouts, key-server failure, sanitized errors and replay.
Existing account, browser binding, optional MFA and concurrency tests remain.

Sources: [Apple identity verification](https://developer.apple.com/documentation/signinwithapple/verifying-a-user)
and [OpenID Connect hybrid-flow validation](https://openid.net/specs/openid-connect-core-1_0-errata2.html#HybridIDTokenValidation).

Limits: these are synthetic cryptographic and HTTP tests, not live Apple acceptance
or actual browser validation. Current Apple claim-shape compatibility and operational
key rotation remain external assurance work. Apple service routing, account-level
isolation and independent review remain open. No production deployment, schema,
existing sessions, user data, social connections or provider grants changed.

Rollback requires no data migration. Preserve strict identity checks in a forward
fix; disable new Apple sign-in if provider validation fails rather than restoring
acceptance of incomplete or conflicting identities. Existing password sign-in and
Zova sessions remain available. Do not replay a consumed authorization code.
