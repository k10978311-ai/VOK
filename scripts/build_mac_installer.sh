#!/usr/bin/env bash
# Build VOK for macOS and create a full install package (.pkg) with welcome and license.
# Run from project root: ./scripts/build_mac_installer.sh
#
# Optional signing and notarization (for distribution):
#   DEVELOPER_ID_APP       "Developer ID Application: Your Name (TEAM_ID)" — sign the app
#   DEVELOPER_ID_INSTALLER "Developer ID Installer: Your Name (TEAM_ID)"   — sign the .pkg
#   NOTARY_KEYCHAIN_PROFILE  Keychain profile for notarytool (or set NOTARY_APPLE_ID, NOTARY_TEAM_ID, NOTARY_APPLE_APP_PASSWORD)
# Then run: ./scripts/build_mac_installer.sh

set -e
SCRIPT_DIR="$(dirname "$0")"
cd "$SCRIPT_DIR/.."
echo "========================================"
echo "  VOK — Build macOS installer (.pkg)"
echo "========================================"

# Build the app first (creates dist/VOK.app)
if [[ ! -d "dist/VOK.app" ]]; then
  echo "Building app..."
  ./scripts/build_mac.sh
else
  echo "Using existing dist/VOK.app (delete it to force rebuild)."
fi

# Version from pyproject.toml (strip quotes and whitespace), fallback 0.1.0
VERSION=$(grep -E '^version\s*=' pyproject.toml | sed -E 's/^version\s*=\s*//' | tr -d '"' | tr -d "'" | xargs)
VERSION=${VERSION:-0.1.0}
PKG_ID="com.vok.app"
PKG_ROOT="dist/pkg_root"
COMPONENT_PKG="dist/VOK-component.pkg"
OUTPUT_PKG="dist/VOK-Install-${VERSION}.pkg"
RESOURCES_DIR="resources/installer"
DIST_XML="dist/Distribution.xml"

# Optional: sign the app with Developer ID before packaging (for distribution)
if [[ -n "${DEVELOPER_ID_APP:-}" ]]; then
  echo "Signing app with Developer ID..."
  codesign --force --deep --sign "$DEVELOPER_ID_APP" --options runtime dist/VOK.app
fi

echo ""
echo "Creating installer package (version ${VERSION})..."

rm -rf "$PKG_ROOT" "$COMPONENT_PKG" "$DIST_XML"
mkdir -p "$PKG_ROOT/Applications"
cp -R dist/VOK.app "$PKG_ROOT/Applications/"

# Component package (payload)
pkgbuild \
  --root "$PKG_ROOT" \
  --identifier "$PKG_ID" \
  --version "$VERSION" \
  --install-location / \
  "$COMPONENT_PKG"

rm -rf "$PKG_ROOT"

# Distribution XML (welcome + license)
cat > "$DIST_XML" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
  <title>VOK</title>
  <welcome file="welcome.rtf"/>
  <license file="license.rtf"/>
  <pkg-ref id="$PKG_ID"/>
  <options customize="never" require-scripts="false"/>
  <choices-outline>
    <line choice="default">
      <line choice="$PKG_ID"/>
    </line>
  </choices-outline>
  <choice id="default"/>
  <choice id="$PKG_ID" visible="false">
    <pkg-ref id="$PKG_ID"/>
  </choice>
  <pkg-ref id="$PKG_ID" version="$VERSION" onConclusion="none">VOK-component.pkg</pkg-ref>
</installer-gui-script>
EOF

# Product package (with welcome/license UI)
if [[ -n "${DEVELOPER_ID_INSTALLER:-}" ]]; then
  productbuild \
    --distribution "$DIST_XML" \
    --resources "$RESOURCES_DIR" \
    --package-path dist \
    --sign "$DEVELOPER_ID_INSTALLER" \
    "$OUTPUT_PKG"
else
  productbuild \
    --distribution "$DIST_XML" \
    --resources "$RESOURCES_DIR" \
    --package-path dist \
    "$OUTPUT_PKG"
fi

rm -f "$DIST_XML" "$COMPONENT_PKG"

# Optional: notarize and staple (for distribution)
if [[ -n "${NOTARY_KEYCHAIN_PROFILE:-}" ]]; then
  echo "Submitting to Apple for notarization..."
  xcrun notarytool submit "$OUTPUT_PKG" --keychain-profile "$NOTARY_KEYCHAIN_PROFILE" --wait
  echo "Stapling notarization ticket..."
  xcrun stapler staple "$OUTPUT_PKG"
  echo "Notarization complete."
elif [[ -n "${NOTARY_APPLE_ID:-}" && -n "${NOTARY_TEAM_ID:-}" && -n "${NOTARY_APPLE_APP_PASSWORD:-}" ]]; then
  echo "Submitting to Apple for notarization..."
  xcrun notarytool submit "$OUTPUT_PKG" \
    --apple-id "$NOTARY_APPLE_ID" \
    --team-id "$NOTARY_TEAM_ID" \
    --password "$NOTARY_APPLE_APP_PASSWORD" \
    --wait
  echo "Stapling notarization ticket..."
  xcrun stapler staple "$OUTPUT_PKG"
  echo "Notarization complete."
fi

echo ""
echo "========================================"
echo "  Installer created: $OUTPUT_PKG"
echo "========================================"
echo ""
echo "Users can double-click the .pkg to see the welcome and license, then install VOK into /Applications."
echo "Run: open $OUTPUT_PKG"
