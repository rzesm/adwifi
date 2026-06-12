_pkgname=adwifi
pkgname=$_pkgname
pkgver=0.1.0-alpha
pkgrel=1
pkgdesc="A libadwaita Wi-Fi manager backed by iwd"
arch=('any')
url="https://github.com/rzesm/adwifi"
license=('GPL-3.0-or-later')

depends=(
    'python-dbus-next'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'python-cairo'
    'iwd'
    'speedtest-cli'
)

makedepends=(
    'python-build'
    'python-installer'
    'python-poetry-core'
)

source=("$_pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$_pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$_pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 adwifi.desktop -t "$pkgdir/usr/share/applications/"
    install -Dm644 adwifi.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/adwifi.svg"
}