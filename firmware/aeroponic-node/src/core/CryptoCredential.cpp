#include "CryptoCredential.h"
#include <mbedtls/sha256.h>
#include <mbedtls/gcm.h>
#include <mbedtls/aes.h>
#include <mbedtls/base64.h>

byte CryptoCredential::aes_key[32];
byte CryptoCredential::aes_iv[12];

void CryptoCredential::deriveKey() {
    uint64_t mac = ESP.getEfuseMac();
    byte mac_bytes[6];
    for (int i = 0; i < 6; i++) {
        mac_bytes[i] = (mac >> (40 - i * 8)) & 0xFF;
    }

    const char* pepper = "AeroponicNodeCredentialV1";
    byte input[30];
    memcpy(input, mac_bytes, 6);
    memcpy(input + 6, pepper, 24);

    byte hash[32];
    mbedtls_sha256_ret(input, sizeof(input), hash, 0);
    memcpy(aes_key, hash, 32);
    for (int i = 0; i < 12; i++) {
        aes_iv[i] = hash[i];
    }
}

String CryptoCredential::base64Encode(const byte* data, size_t length) {
    size_t outLen = 0;
    byte* out = (byte*)calloc(1, ((length + 2) / 3) * 4 + 5);
    if (!out) return "";
    mbedtls_base64_encode(out, ((length + 2) / 3) * 4 + 4, &outLen, data, length);
    String result = String((char*)out);
    free(out);
    return result;
}

size_t CryptoCredential::base64Decode(const String& input, byte* output, size_t maxLen) {
    size_t outLen = 0;
    int ret = mbedtls_base64_decode(output, maxLen, &outLen, (const byte*)input.c_str(), input.length());
    if (ret != 0) return 0;
    return outLen;
}

String CryptoCredential::encrypt(const String& plaintext) {
    if (plaintext.length() == 0) return "";

    byte iv[12];
    for (int i = 0; i < 12; i++) {
        iv[i] = (byte)(esp_random() & 0xFF);
    }

    byte tag[16];
    byte ciphertext[256];
    memset(ciphertext, 0, sizeof(ciphertext));
    memset(tag, 0, sizeof(tag));

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);

    int ret = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES, aes_key, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&gcm);
        return "";
    }

    ret = mbedtls_gcm_crypt_and_tag(&gcm, MBEDTLS_GCM_ENCRYPT,
                                    plaintext.length(),
                                    iv, 12, NULL, 0,
                                    (const byte*)plaintext.c_str(),
                                    ciphertext,
                                    16, tag);

    mbedtls_gcm_free(&gcm);

    if (ret != 0) return "";

    byte combined[12 + 256 + 16];
    memcpy(combined, iv, 12);
    memcpy(combined + 12, ciphertext, plaintext.length());
    memcpy(combined + 12 + plaintext.length(), tag, 16);

    return base64Encode(combined, 12 + plaintext.length() + 16);
}

String CryptoCredential::decrypt(const String& ciphertext) {
    if (ciphertext.length() == 0) return "";

    byte decoded[280];
    size_t decodedLen = base64Decode(ciphertext, decoded, sizeof(decoded));
    if (decodedLen == 0 || decodedLen < 29) return "";

    byte iv[12];
    memcpy(iv, decoded, 12);

    byte plaintext[256];
    memset(plaintext, 0, sizeof(plaintext));

    byte tag[16];
    memcpy(tag, decoded + decodedLen - 16, 16);

    mbedtls_gcm_context gcm;
    mbedtls_gcm_init(&gcm);

    int ret = mbedtls_gcm_setkey(&gcm, MBEDTLS_CIPHER_ID_AES, aes_key, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&gcm);
        return "";
    }

    ret = mbedtls_gcm_crypt_and_tag(&gcm, MBEDTLS_GCM_DECRYPT,
                                    decodedLen - 28,
                                    iv, 12, NULL, 0,
                                    decoded + 12,
                                    plaintext,
                                    16, tag);

    mbedtls_gcm_free(&gcm);

    if (ret != 0) return "";

    return String((char*)plaintext);
}

void CryptoCredential::init() {
    deriveKey();
}
