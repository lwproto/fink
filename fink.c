#include <stdint.h>
#include <string.h>
#include <stdio.h>

static uint8_t reflect(uint8_t b)
{
    uint8_t r = 0;
    for (int i = 0; i < 8; i++) {
        if (b & (1u << i)) {
            r |= (uint8_t)(1u << (7 - i));
        }
    }
    return r;
}

uint8_t crc8_rohc(const uint8_t *data, size_t len)
{
    const uint8_t poly = 0x07u;
    uint8_t crc = 0xFFu;

    for (size_t i = 0; i < len; i++) {
        crc ^= reflect(data[i]);

        for (int bit = 0; bit < 8; bit++) {
            if (crc & 0x80u) {
                crc = (uint8_t)((crc << 1) ^ poly);
            } else {
                crc = (uint8_t)(crc << 1);
            }
        }
    }

    return reflect(crc);
}

int main(void)
{
    const uint8_t text[] = "FINK/1";
    uint8_t crc = crc8_rohc(text, strlen((const char *)text));

    printf("%02X\n", crc);
    return 0;
}