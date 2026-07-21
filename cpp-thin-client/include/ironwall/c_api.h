#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

#ifdef _WIN32
  #define IRONWALL_API __declspec(dllexport)
#else
  #define IRONWALL_API __attribute__((visibility("default")))
#endif

/* Opaque handles */
typedef struct ironwall_client ironwall_client;
typedef struct ironwall_proof ironwall_proof;

/* Lifecycle */
IRONWALL_API ironwall_client* ironwall_client_create(const char* player_id, float max_speed);
IRONWALL_API void ironwall_client_destroy(ironwall_client* c);

/* TEE */
IRONWALL_API int ironwall_client_attest(ironwall_client* c, char* out_quote_hash, size_t out_len);

/* Movement proof (returns 0 ok, non-zero error). out_proof_id must be >= 64 bytes */
IRONWALL_API int ironwall_client_prove_movement(
    ironwall_client* c,
    float from_x, float from_y, float from_z,
    float to_x, float to_y, float to_z,
    uint32_t delta_t_ms,
    char* out_proof_id, size_t proof_id_len,
    char* out_combined_hash, size_t hash_len
);

/* Challenge */
IRONWALL_API int ironwall_client_respond_challenge(
    ironwall_client* c,
    const char* challenge_id,
    char* out_response_id, size_t out_len
);

/* Version */
IRONWALL_API const char* ironwall_version(void);

#ifdef __cplusplus
}
#endif
