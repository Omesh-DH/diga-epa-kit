# Security

## Reporting a vulnerability

Please report security problems privately through GitHub: open the
repository's **Security** tab and choose **Report a vulnerability**. Do not
open a public issue for them.

Only the latest version on `main` is maintained.

## Health data

This kit handles health data formats. It is not a certified medical device and
has not been tested against a real ePA; use synthetic or test data only.

- Never post real patient data in issues, pull requests or vulnerability
  reports. Use synthetic examples.
- The try-it page runs the kit in the browser; input is not sent anywhere. If
  usage counting is switched on, it sends only event names (for example
  `build-ok`), never the input (see README, "The try-it page").
