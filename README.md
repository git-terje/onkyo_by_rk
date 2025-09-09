# Onkyo by RK — v0.1.1

Home Assistant integration for Onkyo / Pioneer network receivers via eISCP.

## Features
- UI setup (Config Flow), SSDP/Zeroconf discovery (confirm)
- `media_player`: turn_on, turn_off, volume_up/down, set_volume_level
- Services:
  - `onkyo_by_rk.dump_capabilities` → writes `/config/onkyo_by_rk/<entry_id>_probe.json`
  - `onkyo_by_rk.debug_files` → logs files under `custom_components/onkyo_by_rk`

## Installation
1. Copy `custom_components/onkyo_by_rk/` into your Home Assistant `config/` directory.
2. Restart Home Assistant.
3. Add the integration via *Settings → Devices & Services*.

## License
MIT
