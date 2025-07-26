# Citations

This project was successful thanks to the following external resources:

## Primary Reference Implementation
- **Repository**: [LeeChSien/homebridge-mitsubishi-electric-aircon](https://github.com/LeeChSien/homebridge-mitsubishi-electric-aircon)
- **License**: Apache-2.0 license
- **Usage**: TypeScript implementation provided the key breakthrough for understanding the AES encryption method and `/smart` endpoint usage
- **Specific files referenced**:
  - `src/MEAircon.ts` - Main device communication
  - `src/utils/crypt.ts` - AES encryption/decryption implementation
  - `src/commands/general.ts` - Control command building
  - `src/commands/extend08.ts` - Extended commands
  - `src/utils/calcFCC.ts` - Checksum calculation

## Referenced from Conversation History
- Original GitHub repository from conversation: References to ECHONET enable commands
- Device IP and communication details provided by user
- Test methodologies and approaches discussed during implementation

## Technical Standards
- **ECHONET Lite specification**: For UDP discovery packet structure (though ultimately not used)
- **AES-CBC encryption**: Standard cryptographic approach
- **HTTP POST requests**: Standard web protocol implementation

## Tools and Libraries Used
- **Python requests**: HTTP client library
- **Python Crypto.Cipher.AES**: AES encryption implementation  
- **Python xml.etree.ElementTree**: XML parsing
- **Python enum and dataclasses**: Type safety and structure

## Key Breakthrough Attribution
The critical insight that enabled this project's success came from the LeeChSien homebridge plugin, which revealed:
1. The use of HTTP `/smart` endpoint instead of UDP ECHONET
2. The static AES key `"unregistered"` 
3. The specific encryption format (IV + data as hex, then base64)
4. The XML payload structure for commands

Without this reference implementation, reverse-engineering the MAC-577IF-2E protocol would have been significantly more challenging.
