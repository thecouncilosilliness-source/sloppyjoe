# HiveBridge launch notes

HiveBridge is publicly reviewable code, not a public AI service.

## Test the source (no API charges)
Download [the source archive](./HiveBridge-v0.1-source.tar.xz), then:

```sh
mkdir hivebridge-local && cd hivebridge-local
tar -xJf ../HiveBridge-v0.1-source.tar.xz
python3 -m unittest discover -s tests -v
python3 -m hivebridge demo --mode council --text "Council readiness check"
```

The archive was locally tested before publication (six passing tests). In demo mode every reply says SIMULATED.

## Free static website
The self-contained [site/index.html](./site/index.html) is an offline simulated demo. It makes **no** provider API calls. It can be hosted on GitHub Pages for eligible public repositories without a paid hosting plan.

To publish the site: use repository **Settings → Pages → Build and deployment → GitHub Actions**, then run the `HiveBridge Pages` workflow manually (or add automatic deployment after first validation). A GitHub Pages site is *not* implied merely by a committed HTML file.

Do not point `ainunnaki.live` DNS at GitHub until the site is working and GitHub has verified the custom domain. Avoid any secrets or personal material in public pages.

## Live Council connections
Live multi-provider service requires separate accounts, credentials, user-approved data sharing, controlled costs, and private hosting. This demo cannot access consumer ChatGPT, Copilot, Meta Muse, or their conversation memories. Never commit secrets. The network backend binds to localhost by default; do not expose it to the open internet without stronger protections.

These are foundations, not an autonomous agent launch.
