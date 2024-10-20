# self-labeler

A [Bluesky](https://bsky.social/)/[AT Protocol](https://atproto.com/)'s [labeler aka mod service](https://bsky.social/about/blog/4-13-2023-moderation) that emits the custom [self-labels](https://atproto.com/specs/label#self-labels-in-records) that already exist inside records.

Apart from the self labels built into [bsky.app](https://bsky.app/), other custom self-labels are often not displayed or handled by clients. This surfaces those labels and makes them visible.

[Background discussion.](https://github.com/bluesky-social/atproto/discussions/2885)


## Setup

* Make a new Bluesky account.
* Convert it to a labeler repo by adding an `#atproto_labeler` service endpoint and `#atproto_label` signing key:
  * `npm install [@skyware/labeler](https://github.com/skyware-js/labeler)`
  * `npx @skyware/labeler setup`
* Convert the base64 raw bytes private key that `@skyware/labeler setup` prints into PEM:
    ```
    $ node
    const { fromBytes, toBytes } = await import("@atcute/cbor");
    fromBytes({'$bytes': '[base64 byte string]'})
    Uint8Array(32) [...]
    
    $ python
    privbytes = bytes([...])  # from above
    
    from cryptography.hazmat.primitives.asymmetric import ec
    privkey = ec.derive_private_key(int.from_bytes(privbytes), ec.SECP256K1())
    
    # `EllipticCurvePublicKey.from_encoded_point` is also close, but there's no corresponding `EllipticCurvePrivateKey.from_encoded_point`
    
    # now, sign something and check that it verifies
    signed = arroba.util.sign({'x': 'y'}, privkey)
    did_doc = did.resolve('did:plc:4wgmwsq4t3tg55ffl3r7ocec')  # self-labeler.snarfed.org
    pubkey = did.decode_did_key(did_doc['verificationMethod'][1]['publicKeyMultibase'])
    arroba.util.verify_sig(signed, pubkey)
    # should be True
    
    # PEM-encode private key
    from cryptography.hazmat.primitives import serialization
    with open('privkey.atproto_label.pem', 'wb') as f:
        f.write(privkey.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    ```
