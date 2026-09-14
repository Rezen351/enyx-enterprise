#ifndef CRYPTO_CREDENTIAL_H
#define CRYPTO_CREDENTIAL_H

#include <Arduino.h>

class CryptoCredential {
public:
    static void init();
    static String encrypt(const String& plaintext);
    static String decrypt(const String& ciphertext);

private:
    static void deriveKey();
    static String base64Encode(const byte* data, size_t length);
    static size_t base64Decode(const String& input, byte* output, size_t maxLen);

    static byte aes_key[32];
    static byte aes_iv[12];
};

#endif
