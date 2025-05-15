# راهنمای انتشار FlashGet در GitHub | Instrucciones para publicar FlashGet en GitHub

<div dir="rtl">

# راهنمای انتشار FlashGet در GitHub

این سند دستورالعمل‌های گام به گام برای انتشار پروژه FlashGet در GitHub را ارائه می‌دهد.

## ۱. نصب Git

ابتدا، نیاز دارید Git را روی کامپیوتر خود نصب کنید.

### برای ویندوز:

۱. نصب‌کننده Git را از [git-scm.com](https://git-scm.com/download/win) دانلود کنید.
۲. نصب‌کننده را اجرا کنید و دستورالعمل‌ها را دنبال کنید (می‌توانید از تنظیمات پیش‌فرض استفاده کنید).
۳. پس از نصب، یک پنجره PowerShell یا Command Prompt جدید باز کنید.
۴. نصب را با این دستور بررسی کنید:
   ```
   git --version
   ```

### برای مک:

۱. با Homebrew (اگر نصب کرده‌اید) Git را نصب کنید:
   ```
   brew install git
   ```
   یا نصب‌کننده را از [git-scm.com](https://git-scm.com/download/mac) دانلود کنید
۲. نصب را بررسی کنید:
   ```
   git --version
   ```

### برای لینوکس:

```
sudo apt-get update
sudo apt-get install git
```

با `git --version` بررسی کنید

## ۲. پیکربندی Git

هویت خود را در Git پیکربندی کنید (از ایمیل GitHub خود استفاده کنید):

```
git config --global user.name "نام شما"
git config --global user.email "your.email@example.com"
```

## ۳. ایجاد حساب GitHub

اگر حساب GitHub ندارید:

۱. به [GitHub.com](https://github.com/) بروید
۲. روی "Sign up" کلیک کنید و دستورالعمل‌ها را برای ایجاد حساب دنبال کنید.

## ۴. ایجاد مخزن در GitHub

۱. وارد حساب GitHub خود شوید.
۲. روی دکمه "+" در گوشه بالا سمت راست کلیک کنید و "New repository" را انتخاب کنید.
۳. نام مخزن: "flashget" (یا نامی که ترجیح می‌دهید).
۴. توضیحات (اختیاری): "یک مدیر دانلود مدرن و کارآمد".
۵. گزینه "Public" را انتخاب کنید (یا "Private" اگر می‌خواهید آن را خصوصی نگه دارید).
۶. گزینه "Initialize this repository with a README" را علامت نزنید چون ما قبلاً یکی ایجاد کرده‌ایم.
۷. روی "Create repository" کلیک کنید.

## ۵. آماده‌سازی مخزن محلی

ترمینالی در دایرکتوری پروژه خود باز کنید و دستورات زیر را اجرا کنید:

```
git init
git add .
git commit -m "Commit اولیه مدیر دانلود FlashGet"
```

## ۶. اتصال به GitHub و آپلود کد

GitHub دستورات دقیق را به شما نشان خواهد داد، اما معمولاً چیزی شبیه به این خواهد بود:

```
git remote add origin https://github.com/نام_کاربری_شما/flashget.git
git branch -M main
git push -u origin main
```

`نام_کاربری_شما` را با نام کاربری GitHub خود جایگزین کنید.

## ۷. بررسی انتشار

۱. از مخزن خود در GitHub بازدید کنید: `https://github.com/نام_کاربری_شما/flashget`
۲. باید تمام فایل‌های خود و README.md را در صفحه ببینید.

## ۸. به‌روزرسانی‌های آینده

برای آپلود تغییرات آینده، از این دستورات استفاده کنید:

```
git add .
git commit -m "توضیحات تغییرات انجام شده"
git push
```

## ۹. ملاحظات اضافی

- اگر می‌خواهید مردم به راحتی از برنامه شما استفاده کنند، دستورالعمل‌های واضحی در README.md اضافه کنید.
- می‌توانید لینک مخزن خود را به اشتراک بگذارید تا دیگران آن را دانلود کنند، آزمایش کنند یا مشارکت کنند.
- در نظر بگیرید "Releases" را در GitHub برای نسخه‌های پایدار برنامه خود اضافه کنید.

تبریک! پروژه FlashGet شما اکنون در GitHub در دسترس است، که به اشتراک‌گذاری و همکاری آن را آسان می‌کند.

</div>

---

# Instrucciones para publicar FlashGet en GitHub

Este documento proporciona instrucciones paso a paso para publicar tu proyecto FlashGet en GitHub.

## 1. Instalar Git

Primero, necesitas instalar Git en tu computadora.

### Para Windows:

1. Descarga el instalador de Git desde [git-scm.com](https://git-scm.com/download/win).
2. Ejecuta el instalador y sigue las instrucciones (puedes usar la configuración predeterminada).
3. Una vez instalado, abre una nueva ventana de PowerShell o Command Prompt.
4. Verifica la instalación con el comando:
   ```
   git --version
   ```

### Para Mac:

1. Instala Git con Homebrew (si lo tienes instalado):
   ```
   brew install git
   ```
   O descarga el instalador desde [git-scm.com](https://git-scm.com/download/mac)
2. Verifica la instalación:
   ```
   git --version
   ```

### Para Linux:

```
sudo apt-get update
sudo apt-get install git
```

Verifica con: `git --version`

## 2. Configurar Git

Configura tu identidad en Git (usa tu correo electrónico de GitHub):

```
git config --global user.name "Tu Nombre"
git config --global user.email "tu.email@example.com"
```

## 3. Crear una cuenta de GitHub

Si no tienes una cuenta de GitHub:

1. Ve a [GitHub.com](https://github.com/)
2. Haz clic en "Sign up" y sigue las instrucciones para crear una cuenta.

## 4. Crear un repositorio en GitHub

1. Inicia sesión en tu cuenta de GitHub.
2. Haz clic en el botón "+" en la esquina superior derecha y selecciona "New repository".
3. Nombre del repositorio: "flashget" (o el nombre que prefieras).
4. Descripción (opcional): "Un gestor de descargas moderno y eficiente".
5. Marca la opción "Public" (o "Private" si prefieres mantenerlo privado).
6. NO marques "Initialize this repository with a README" porque ya creamos uno.
7. Haz clic en "Create repository".

## 5. Inicializar y preparar el repositorio local

Abre una terminal en el directorio de tu proyecto y ejecuta los siguientes comandos:

```
git init
git add .
git commit -m "Commit inicial de FlashGet Download Manager"
```

## 6. Conectar con GitHub y subir el código

GitHub te mostrará los comandos exactos, pero generalmente serán algo como:

```
git remote add origin https://github.com/TU_USUARIO/flashget.git
git branch -M main
git push -u origin main
```

Reemplaza `TU_USUARIO` con tu nombre de usuario de GitHub.

## 7. Verificar la publicación

1. Visita tu repositorio en GitHub: `https://github.com/TU_USUARIO/flashget`
2. Deberías ver todos tus archivos y el README.md en la página.

## 8. Actualizaciones Futuras

Para subir cambios futuros, usa estos comandos:

```
git add .
git commit -m "Descripción de los cambios realizados"
git push
```

## 9. Consideraciones Adicionales

- Si quieres que la gente pueda utilizar fácilmente tu programa, considera agregar instrucciones claras en el README.md.
- Puedes compartir el enlace de tu repositorio para que otros lo descarguen, lo prueben o contribuyan.
- Considera agregar "Releases" en GitHub para versiones estables de tu aplicación.

¡Felicidades! Tu proyecto FlashGet ahora está disponible en GitHub, lo que facilita su compartición y colaboración. 