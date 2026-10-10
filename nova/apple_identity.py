"""Validate Apple hybrid-flow identities before account access or mutation."""
import base64
import hashlib
import secrets

import jwt

from .security import hash_api_key


def verify_identity(token, jwks, client_id, nonce_hash, *, code=None):
    if not isinstance(token, str) or not token or len(token)>16384:
        raise jwt.InvalidTokenError('Invalid identity token')
    required=['iss','aud','exp','iat','sub','nonce']
    if code is not None:required.append('c_hash')
    claims=jwt.decode(token,jwks.get_signing_key_from_jwt(token).key,
        algorithms=['RS256'],audience=client_id,issuer='https://appleid.apple.com',
        options={'require':required,'strict_aud':True})
    if (not isinstance(claims.get('sub'),str) or not 1<=len(claims['sub'])<=255
        or not isinstance(claims.get('nonce'),str)
        or not secrets.compare_digest(hash_api_key(claims['nonce']),nonce_hash)
        or any(type(claims.get(k)) is not int for k in ('iat','exp'))
        or ('azp' in claims and claims['azp']!=client_id)):
        raise jwt.InvalidTokenError('Invalid identity claims')
    if 'email' in claims and not isinstance(claims['email'],str):
        raise jwt.InvalidTokenError('Invalid email claim')
    if 'email_verified' in claims and not (type(claims['email_verified']) is bool
            or claims['email_verified'] in ('true','false')):
        raise jwt.InvalidTokenError('Invalid verification claim')
    if code is not None:
        try:
            expected=base64.urlsafe_b64encode(hashlib.sha256(code.encode('ascii')).digest()[:16]).rstrip(b'=').decode()
        except (UnicodeEncodeError,AttributeError):
            raise jwt.InvalidTokenError('Invalid authorization code') from None
        value=claims.get('c_hash')
        if not isinstance(value,str) or not secrets.compare_digest(value.encode(),expected.encode()):
            raise jwt.InvalidTokenError('Authorization code does not match')
    return claims
