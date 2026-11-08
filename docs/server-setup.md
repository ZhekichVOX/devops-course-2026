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

## 8. Веб-сервер

- Пакет: nginx 1.24.0 (sudo apt install -y nginx), служба включена в автозапуск.
- Конфигурация ресурса: /etc/nginx/sites-available/devops-site, активирована ссылкой в /etc/nginx/sites-enabled/. Стандартный ресурс отключён: удалена ссылка /etc/nginx/sites-enabled/default.
- Блок 1 (порт 80, server_name devops.local): return 301 https://$host$request_uri.
- Блок 2 (порты 443 ssl, IPv4 и IPv6, server_name devops.local): ssl_protocols TLSv1.2 TLSv1.3; root /var/www/devops-site; index index.html; location / { try_files $uri $uri/ =404; }; error_page 404 /404.html; журналы /var/log/nginx/devops-site.access.log и /var/log/nginx/devops-site.error.log.
- Каталог ресурса: /var/www/devops-site, владелец devops:devops, права 755 на каталоги и 644 на файлы. Содержимое доставляется scripts/deploy.sh (rsync -az --delete --chmod=D755,F644).
- Сертификат: /etc/ssl/certs/devops.crt, владелец root, права 644, самоподписанный, SAN DNS:devops.local, срок действия 365 дней (до 8 ноября 2027).
- Закрытый ключ: /etc/ssl/private/devops.key, владелец root, права 600.
- Команда формирования сертификата:

      sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/devops.key -out /etc/ssl/certs/devops.crt -subj "/CN=devops.local" -addext "subjectAltName=DNS:devops.local"

- Применение конфигурации: sudo nginx -t && sudo systemctl reload nginx (restart не использовать).
- Межсетевой экран: порты 80/tcp и 443/tcp разрешены правилами из раздела 6.
- Заголовок HSTS не добавляется (самоподписанный сертификат).
- Снимок состояния: 04-nginx-https.
