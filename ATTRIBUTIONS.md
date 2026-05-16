# Attributions and Third-Party Credits

This project builds upon the excellent work of several open source projects and Docker container maintainers. We gratefully acknowledge their contributions.

## Docker Services

### PyPowerwall

- **Image**: `jasonacox/pypowerwall:latest`
- **Author**: Jason Cox ([jasonacox](https://github.com/jasonacox))
- **Repository**: <https://github.com/jasonacox/pypowerwall>
- **License**: MIT License
- **Purpose**: Python proxy server for accessing Tesla Powerwall data

### NUT UPS Daemon

- **Image**: `instantlinux/nut-upsd:latest`
- **Maintainer**: Rich Braun ([instantlinux](https://github.com/instantlinux))
- **Repository**: <https://github.com/instantlinux/docker-nut-upsd>
- **License**: GPL v2
- **Purpose**: Network UPS Tools daemon for UPS status monitoring

## Python Libraries

### Core Dependencies

- **aiohttp** - Apache 2.0 License - Async HTTP client/server framework
- **pydantic-settings** - MIT License - Settings management using Pydantic
- **Jinja2** - BSD License - Template engine for dashboard rendering
- **fastapi** - MIT License - Web framework for the dashboard API
- **uvicorn** - BSD License - ASGI server
- **aiosmtplib** - MIT License - Async SMTP client
- **voluptuous** - BSD License - Data validation library

## Acknowledgments

- **Tesla** - For creating the Powerwall battery system
- **NUT Project** - Network UPS Tools team for the UPS monitoring protocol
- **Home Assistant Community** - For the integration framework and best practices

## License Note

All third-party components retain their original licenses. This project respects the open source licenses of all dependencies and encourages users to review the licenses of the Docker images and Python packages listed above.

---

*If you are a maintainer of one of the projects listed above and would like your attribution updated or removed, please open an issue.*
