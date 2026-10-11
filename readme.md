# Adwifi

Adwifi is a [libadwaita](https://github.com/GNOME/libadwaita) Wi-Fi management app designed for [veri](https://github.com/rzesm/veri) but suitable for any other Arch Linux setup. It interfaces [iwd](https://wiki.archlinux.org/title/Iwd) directly, making it ideal for minimal configurations.

Adwifi was inspired by [Adwaita Bluetooth](https://github.com/ezratweaver/adw-bluetooth/)'s aesthetic.

### Features

- Explicit network adapter selection
- Support for all standard network security protocols
- Connection speed tester

### Interface

![](assets/interface.png)
![](assets/speed_test.png)

### Installation

#### AUR

Install as an AUR package (example below with [yay](https://github.com/jguer/yay)):
```
yay -S adwifi-git
```

#### Manual

```
git clone https://github.com/rzesm/adwifi
cd adwifi/package
makepkg -si
```