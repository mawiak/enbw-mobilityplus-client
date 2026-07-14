# EnBW mobility+ Client

> ⚠️ **IMPORTANT DISCLAIMER**: This is an **unofficial, reverse-engineered** client library for the EnBW mobility+ API. EnBW does not provide a public API, so this library was created by analyzing the official mobile app's network traffic. Use at your own risk and responsibility.

Python client library for the EnBW mobility+ API, allowing you to programmatically access your charging history and account information.

## Features

- 🔐 OAuth2 PKCE authentication flow
- 📊 Fetch charging history with detailed session information
- 👤 Access user profile and account information
- 🐍 Modern Python 3.11+ with full type hints
- 🔄 Automatic token refresh handling
- 🍪 Session management with proper cookie handling

## Installation

```bash
pip install enbw-mobilityplus-client
```

## Quick Start

```python
from enbw_mobilityplus_client import EnBWMobilityPlusClient

# Initialize the client
client = EnBWMobilityPlusClient()

# Login with your EnBW mobility+ credentials
client.login("your-email@example.com", "your-password")

# Get your charging history
history = client.get_charging_history(limit=10)

for session in history:
    print(f"{session.started_at}: {session.energy_in_kwh} kWh at {session.address}")

# Get user profiles
profiles = client.get_profiles()
print(f"Account ID: {profiles[0].charging_account_id}")

# Close the client when done
client.close()
```

Or use it as a context manager:

```python
with EnBWMobilityPlusClient() as client:
    client.login("your-email@example.com", "your-password")
    history = client.get_charging_history()
```

## API Coverage

Currently implemented endpoints:

- ✅ OAuth2 PKCE Authentication Flow
- ✅ Token Refresh
- ✅ User Profiles (`/api/v1/profiles`)
- ✅ Charging History (`/emobility-complete/api/v2/charginghistory`)
- ⏳ Charging Stations / Map Search (planned)
- ⏳ Real-time charging session status (planned)
- ⏳ Tariff information (planned)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/mawiak/enbw-mobilityplus-client.git
cd enbw-mobilityplus-client

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Code Quality

This project uses:
- **Black** for code formatting
- **isort** for import sorting
- **Flake8** for linting
- **pytest** for testing

Run checks:
```bash
black src/
isort src/
flake8 src/
pytest
```

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `test:` - Test changes

Example: `feat: add charging session retrieval method`

### Release Process

Releases are automated using semantic-release:
1. Push commits to `main` following conventional commit format
2. GitHub Actions automatically:
   - Determines version bump (major/minor/patch)
   - Updates CHANGELOG.md
   - Creates GitHub release
   - Publishes to PyPI

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes using conventional commits
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Disclaimer & Terms of Use

**READ CAREFULLY BEFORE USING THIS LIBRARY**

### Reverse Engineering Notice

This library was created by **reverse-engineering** the EnBW mobility+ mobile application's network traffic, as **EnBW does not provide an official public API**. The implementation is based on analyzing HTTP requests and responses between the official app and EnBW's backend services.

### No Affiliation

This project is **NOT**:
- Affiliated with, endorsed by, or supported by EnBW Energie Baden-Württemberg AG
- An official EnBW product or service
- Guaranteed to work or be maintained

### No Warranty & Liability

This software is provided **"AS IS"**, without warranty of any kind, express or implied, including but not limited to:
- Warranties of merchantability
- Fitness for a particular purpose
- Non-infringement

**The authors and contributors:**
- Accept **NO liability** for any damages, data loss, or issues arising from use of this library
- Are **NOT responsible** for any violations of EnBW's Terms of Service
- Provide **NO guarantee** that this library will continue to work (EnBW may change their API at any time)

### Responsible Use

By using this library, you agree to:

✅ **DO:**
- Use it only with your own EnBW mobility+ account
- Respect EnBW's infrastructure and rate limits
- Use it for personal, non-commercial purposes
- Keep your credentials secure
- Comply with all applicable laws and regulations

❌ **DON'T:**
- Use it for unauthorized access to other accounts
- Abuse or overload EnBW's API infrastructure
- Use it for commercial purposes without authorization
- Scrape or collect data at scale
- Violate EnBW's Terms of Service
- Use it for any malicious or illegal activities

### Terms of Service

Using this library to access EnBW's services means you are subject to [EnBW mobility+ Terms of Service](https://www.enbw.com). **You are solely responsible** for ensuring your use complies with these terms.

### API Changes

EnBW may change, break, or restrict their API at any time without notice. This library may stop working without warning, and the maintainers are under no obligation to update it.

### Your Responsibility

**YOU** are responsible for:
- Any consequences of using this library
- Ensuring compliance with EnBW's Terms of Service
- Protecting your account credentials
- Any damages or issues that arise from your use

### Summary

**Use this library at your own risk and responsibility. The authors provide this tool for educational and personal use only, with no guarantees or support.**

## Support

If you encounter any issues or have questions:
- Open an issue on [GitHub](https://github.com/mawiak/enbw-mobilityplus-client/issues)
- Check the [documentation](https://github.com/mawiak/enbw-mobilityplus-client)

## Acknowledgments

Inspired by the [elli-client](https://github.com/mawiak/elli-client) project.
