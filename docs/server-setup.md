# Конфигурация виртуальной машины devops-vm

## 1. Параметры машины
- Гипервизор: VirtualBox 7.x (хост — Windows)
- Гостевая ОС: Ubuntu Server 24.04.5 LTS, 64-bit (установка Use an entire disk, OpenSSH server)
- Имя в VirtualBox: devops-vm
- Оперативная память: 2048 МБ
- Процессор: 2 ядра
- Диск: 25 ГБ, динамически расширяемый
- Имя узла: devops-vm (FQDN devops-vm.devops.local)

## 2. Сетевые интерфейсы
| Интерфейс | Адаптер VirtualBox | Адрес | Назначение |
|---|---|---|---|
| enp0s3 | Адаптер 1, NAT | 10.0.2.15/24 (DHCP) | выход в Интернет, пакеты |
| enp0s8 | Адаптер 2, Host-only «VirtualBox Host-Only Ethernet Adapter» (без #2) | 192.168.56.101/24 (статически) | доступ с хоста, браузер |

Адрес enp0s8 задан в /etc/netplan/99-enp0s8.yaml (права 600):

    network:
      version: 2
      ethernets:
        enp0s8:
          dhcp4: no
          addresses: [192.168.56.101/24]

Применение: `sudo netplan apply`. Адрес хоста в сети Host-only: 192.168.56.1.

На хосте (Windows) в C:\Windows\System32\drivers\etc\hosts добавлена строка `192.168.56.101    devops.local`.
На сервере в /etc/hosts: `127.0.1.1 devops-vm.devops.local devops-vm`.

## 3. Правило проброса портов
Адаптер 1 (NAT), правило «ssh»: TCP, хост 127.0.0.1:2222 → гость 2222
(по умолчанию гостевой порт 22; после смены порта SSH изменён на 2222).

## 4. Учётные записи
| Имя | Группы | Аутентификация |
|---|---|---|
| devops | devops, sudo, users | SSH по ключу ED25519; sudo по паролю |
| vboxuser | учётная запись установщика, sudo | только консоль VirtualBox (SSH запрещён директивой AllowUsers) |

Ключ клиента: ~/.ssh/devops_vm (хост), открытая часть в /home/devops/.ssh/authorized_keys.
Права: ~/.ssh 700, authorized_keys 600. На хосте ~/.ssh/config содержит блок
`Host devops` (HostName 127.0.0.1, Port 2222, User devops, IdentityFile ~/.ssh/devops_vm, IdentitiesOnly yes).
Вход: `ssh devops` либо `ssh -p 2222 devops@devops.local`.

## 5. Служба SSH
- Эталонная копия: /etc/ssh/sshd_config.backup; основной файл не изменялся
- Файл настроек: /etc/ssh/sshd_config.d/99-hardening.conf

      Port 2222
      PermitRootLogin no
      PasswordAuthentication no
      PubkeyAuthentication yes
      PermitEmptyPasswords no
      MaxAuthTries 3
      LoginGraceTime 30
      AllowUsers devops
      X11Forwarding no
      ClientAliveInterval 300
      ClientAliveCountMax 2

- Сокет-активация отключена: `sudo systemctl disable --now ssh.socket`, `sudo systemctl enable --now ssh.service`
- Проверка: `sudo sshd -t`, `sudo sshd -T | grep -Ei "^(port|permitrootlogin|passwordauthentication|maxauthtries|allowusers)"`, `sudo ss -tlnp | grep sshd`
- Если ssh.socket включить обратно, порт вернётся к 22

## 6. Правила межсетевого экрана (ufw)
Политики: `default deny incoming`, `default allow outgoing`. Журнал: `ufw logging medium`.

Порядок: правила создаются до `ufw enable`.

    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw limit 2222/tcp comment 'SSH rate-limited'
    sudo ufw allow 80/tcp comment 'HTTP'
    sudo ufw allow 443/tcp comment 'HTTPS'
    sudo ufw enable

| Порт | Действие | Комментарий |
|---|---|---|
| 2222/tcp | LIMIT IN | SSH, блокировка при 6+ соединениях за 30 с |
| 80/tcp | ALLOW IN | HTTP (ПР №6) |
| 443/tcp | ALLOW IN | HTTPS |

Не использовать `ufw allow ssh`: имя ssh соответствует порту 22 по /etc/services.

## 7. Снимки состояния
| Имя | Момент создания |
|---|---|
| 01-clean-install | 03.11.2026, после установки ОС |
| 03-ssh-hardened | 08.11.2026 14:34, после усиления защиты SSH |
| pr5-done | 08.11.2026 15:18, ПР №5 выполнена полностью |

Снимок 02-keys-configured не создавался.
