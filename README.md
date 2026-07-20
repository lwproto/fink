# Fink
> Lightweight discrete protocol for resource-constrained IoT devices

## About
**Fink** is a lightweight discrete protocol designed for resource-constrained IoT devices with limited bandwidth.

## Architecture
### Frame structure
The Fink frames are called **fink-o-gramm** and have their own structure.

#### Fields Description
| Field      | Size        | Description                                                        |
|------------|-------------|--------------------------------------------------------------------|
| `Magic`    | 1 byte      | Protocol identifier calculated by the Together method (see below). |
| `Flags`    | 1 byte      | Frame flags (see below).                                           |
| `Length`   | 1 byte      | Length of the payload.                                             |
| `Payload`  | 0~255 bytes | User data up to 255 bytes.                                         |
| `Checksum` | 1 byte      | CRC-8/ROHC checksum of the frame.                                  |
---

### Magic & "Together" method

The **Magic** field is a one-byte identifier that uniquely represents both the protocol and its version. It is calculated using the **Together** method.

The Together method computes the **CRC-8/ROHC** checksum of the following ASCII string:

```text
"{PROTOCOL}/{version}"
```

where:

* **PROTOCOL** — protocol identifier written in uppercase letters.
* **version** — sequential protocol version number.

The resulting CRC-8/ROHC value becomes the **Magic** field of every frame.

#### Purpose

The Together method serves two purposes:

1. **Explicit protocol filtering** — frames belonging to other protocols are immediately rejected because their Magic value differs.
2. **Automatic version discrimination** — different protocol versions produce different Magic values, allowing incompatible versions to be distinguished without transmitting the version number separately.

This approach eliminates the need to transmit the protocol identifier and version separately, reducing frame overhead while preserving reliable identification.

**Example**
\
For protocol **FINK** version **1**:

```text
Input string: "FINK/1"
CRC-8/ROHC:   0xDB
```

Therefore, every frame of **FINK v1** begins with the following Magic byte:

```text
Magic = 0xDB
```
---

### Frame Flags

The **Flags** field is a one-byte bitmask that contains frame attributes and control information. Each bit represents an independent flag and may be set or cleared without affecting the others.

#### Flags Bitmask Description

| Flag          | Bit | Description                                                                                                                                              |
| ------------- | :-: | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `URGENT`      |  0  | Marks the frame as high priority. The receiver should process it as soon as possible.                                                                    |
| `REQUIRE_ACK` |  1  | Requests an acknowledgment from the receiver. After successful processing, an `ACK` frame should be sent in response.                                    |
| `ACK`         |  2  | Indicates that the frame is an acknowledgment for a previously received frame. The payload may be empty unless the protocol extension defines otherwise. |
| *Reserved*    | 3–7 | Reserved for future protocol extensions. These bits **must** be transmitted as `0` and ignored by receivers.                                             |

#### Notes

* Multiple flags may be set simultaneously unless explicitly prohibited by a protocol extension.
* Reserved bits should always remain cleared to ensure forward compatibility with future protocol versions.
