# SPDX-License-Identifier: AGPL-3.0-only
"""The printable sheet: two window cards, two strips, a 50 mm verification line and instructions.

The drawing is the same `draw_card` the detector and the 3D print use, painted into SVG and laid out by
WeasyPrint with the same fonts as the reports, so the sheet reads in every language neVus speaks.
"""

from __future__ import annotations

from html import escape
from typing import TypedDict

from nevus.cv.card import GREY, STRIP, WINDOW, draw_card
from nevus.languages import direction, normalise
from nevus.reports.render import pdf_from_html

PAGES = {"a4": (210.0, 297.0), "letter": (215.9, 279.4)}  # millimetres
HTML = """<!doctype html>
<html lang="{lang}" dir="{dir}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@font-face {{ font-family: Epilogue; src: url("../fonts/Epilogue-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: Epilogue; src: url("../fonts/Epilogue-SemiBold.ttf"); font-weight: 600; }}
@page {{ size: {width}mm {height}mm; margin: 0; }}
html, body {{ margin: 0; padding: 0; }}
svg {{ display: block; }}
text {{ font-family: Epilogue, "Noto Sans", "Droid Sans Fallback", "DejaVu Sans", sans-serif; }}
</style>
</head>
<body>{svg}</body>
</html>
"""


class SheetText(TypedDict):
    title: str
    lines: list[str]
    line: str
    spares: str


TEXT: dict[str, SheetText] = {
    "en": {
        "title": "neVus reference card v1",
        "lines": [
            "Print at 100 % (actual size, no fit to page) on matte card or matte photo paper.",
            "Before first use, measure the line above with a ruler. It must be 50 mm.",
            "If it is not, enter what you measured in neVus (Settings > Reference card): measurements are corrected.",
            "Cut along the thin outline and cut out the 24 mm window. Place the window over the mark,",
            "flat on the skin, and photograph from above. Use the strip where the card cannot lie flat.",
            "Glossy paper and glossy lamination cause reflections that hide the markers.",
            "The card touches skin: keep it personal, wipe it with alcohol, replace it when worn.",
        ],
        "line": "50 mm",
        "spares": "Grey squares for a 3D-printed card: cut one out and glue it over the card's black square.",
    },
    "es": {
        "title": "Tarjeta de referencia neVus v1",
        "lines": [
            "Imprime al 100 % (tamaño real, sin ajustar a la página) en cartulina o papel fotográfico mate.",
            "Antes del primer uso, mide la línea de arriba con una regla. Debe medir 50 mm.",
            "Si no, introduce lo que mediste en neVus (Ajustes > Tarjeta de referencia): las medidas se corrigen.",
            "Recorta por el contorno fino y recorta la ventana de 24 mm. Pon la ventana sobre la marca,",
            "plana sobre la piel, y fotografía desde arriba. Usa la tira donde la tarjeta no quede plana.",
            "El papel brillante y el plastificado brillante producen reflejos que ocultan los marcadores.",
            "La tarjeta toca la piel: es personal, límpiala con alcohol y cámbiala cuando se gaste.",
        ],
        "line": "50 mm",
        "spares": "Cuadrados grises para una tarjeta impresa en 3D: recorta uno y pégalo sobre el cuadrado negro.",
    },
    "pt": {
        "title": "Cartão de referência neVus v1",
        "lines": [
            "Imprima a 100 % (tamanho real, sem ajustar à página) em cartolina ou papel fotográfico mate.",
            "Antes da primeira utilização, meça a linha acima com uma régua. Deve medir 50 mm.",
            "Se não medir, introduza o que mediu no neVus (Definições > Cartão de referência): as medições são "
            "corrigidas.",
            "Recorte pelo contorno fino e recorte a janela de 24 mm. Coloque a janela sobre a marca,",
            "plana sobre a pele, e fotografe de cima. Use a tira onde o cartão não assente plano.",
            "O papel brilhante e a plastificação brilhante provocam reflexos que escondem os marcadores.",
            "O cartão toca na pele: é pessoal, limpe-o com álcool e substitua-o quando estiver gasto.",
        ],
        "line": "50 mm",
        "spares": "Quadrados cinzentos para um cartão impresso em 3D: recorte um e cole-o sobre o quadrado preto do "
        "cartão.",
    },
    "ca": {
        "title": "Targeta de referència neVus v1",
        "lines": [
            "Imprimeix al 100 % (mida real, sense ajustar a la pàgina) en cartolina o paper fotogràfic mat.",
            "Abans del primer ús, mesura la línia de dalt amb una regla. Ha de fer 50 mm.",
            "Si no, introdueix al neVus el que has mesurat (Ajustos > Targeta de referència): les mesures es "
            "corregeixen.",
            "Retalla pel contorn fi i retalla la finestra de 24 mm. Posa la finestra sobre la marca,",
            "plana sobre la pell, i fotografia des de dalt. Fes servir la tira on la targeta no quedi plana.",
            "El paper brillant i el plastificat brillant produeixen reflexos que amaguen els marcadors.",
            "La targeta toca la pell: és personal, neteja-la amb alcohol i canvia-la quan s'hagi gastat.",
        ],
        "line": "50 mm",
        "spares": "Quadrats grisos per a una targeta impresa en 3D: retalla'n un i enganxa'l sobre el quadrat negre "
        "de la targeta.",
    },
    "gl": {
        "title": "Tarxeta de referencia neVus v1",
        "lines": [
            "Imprime ao 100 % (tamaño real, sen axustar á páxina) en cartolina ou papel fotográfico mate.",
            "Antes do primeiro uso, mide a liña de arriba cunha regra. Debe medir 50 mm.",
            "Se non, introduce en neVus o que mediches (Axustes > Tarxeta de referencia): as medidas corríxense.",
            "Recorta polo contorno fino e recorta a fiestra de 24 mm. Pon a fiestra sobre a marca,",
            "plana sobre a pel, e fotografa desde arriba. Usa a tira onde a tarxeta non quede plana.",
            "O papel brillante e o plastificado brillante producen reflexos que agochan os marcadores.",
            "A tarxeta toca a pel: é persoal, límpaa con alcol e cámbiaa cando se desgaste.",
        ],
        "line": "50 mm",
        "spares": "Cadrados grises para unha tarxeta impresa en 3D: recorta un e pégao sobre o cadrado negro da "
        "tarxeta.",
    },
    "eu": {
        "title": "neVus erreferentzia-txartela v1",
        "lines": [
            "Inprimatu % 100ean (benetako tamaina, orrira doitu gabe) kartulina mate batean edo argazki-paper mate "
            "batean.",
            "Lehen erabili aurretik, neurtu goiko lerroa erregela batekin. 50 mm izan behar du.",
            "Hala ez bada, sartu neVus-en neurtu duzuna (Ezarpenak > Erreferentzia-txartela): neurketak zuzentzen "
            "dira.",
            "Moztu ertz fina jarraituz eta moztu 24 mm-ko leihoa. Jarri leihoa markaren gainean,",
            "larruazalaren aurka lau, eta atera argazkia goitik. Erabili tira txartela lau jarri ezin den tokian.",
            "Paper distiratsuak eta laminazio distiratsuak islak sortzen dituzte, eta horiek markatzaileak ezkutatzen "
            "dituzte.",
            "Txartelak larruazala ukitzen du: pertsonala da, garbitu alkoholarekin eta ordezkatu higatzen denean.",
        ],
        "line": "50 mm",
        "spares": "Grisezko koadroak 3D bidez inprimatutako txartel baterako: moztu bat eta itsatsi txartelaren "
        "koadro beltzaren gainean.",
    },
    "fr": {
        "title": "Carte de référence neVus v1",
        "lines": [
            "Imprimez à 100 % (taille réelle, sans ajustement à la page) sur du carton mat ou du papier photo mat.",
            "Avant la première utilisation, mesurez la ligne ci-dessus avec une règle. Elle doit faire 50 mm.",
            "Sinon, saisissez ce que vous avez mesuré dans neVus (Réglages > Carte de référence) : les mesures sont "
            "corrigées.",
            "Découpez le long du fin contour et découpez la fenêtre de 24 mm. Placez la fenêtre sur la marque,",
            "à plat sur la peau, et photographiez de dessus. Utilisez la bande là où la carte ne peut pas rester à "
            "plat.",
            "Le papier brillant et la plastification brillante créent des reflets qui masquent les repères.",
            "La carte touche la peau : gardez-la personnelle, essuyez-la à l'alcool, remplacez-la quand elle est usée.",
        ],
        "line": "50 mm",
        "spares": "Carrés gris pour une carte imprimée en 3D : découpez-en un et collez-le sur le carré noir de la "
        "carte.",
    },
    "it": {
        "title": "Tessera di riferimento neVus v1",
        "lines": [
            "Stampa al 100 % (dimensione reale, senza adattare alla pagina) su cartoncino opaco o carta fotografica "
            "opaca.",
            "Prima del primo utilizzo, misura la linea qui sopra con un righello. Deve essere di 50 mm.",
            "Se non lo è, inserisci in neVus quanto hai misurato (Impostazioni > Tessera di riferimento): le misure "
            "vengono corrette.",
            "Ritaglia lungo il contorno sottile e ritaglia la finestra da 24 mm. Appoggia la finestra sul segno,",
            "ben piatta sulla pelle, e fotografa dall'alto. Usa la striscia dove la tessera non può stare piatta.",
            "La carta lucida e la plastificazione lucida causano riflessi che nascondono i marcatori.",
            "La tessera tocca la pelle: tienila personale, puliscila con alcol e sostituiscila quando è consumata.",
        ],
        "line": "50 mm",
        "spares": "Quadrati grigi per una tessera stampata in 3D: ritaglia un quadrato e incollalo sul quadrato nero "
        "della tessera.",
    },
    "de": {
        "title": "neVus-Referenzkarte v1",
        "lines": [
            "Drucke mit 100 % (Originalgröße, nicht an die Seite anpassen) auf mattem Karton oder mattem Fotopapier.",
            "Miss vor der ersten Benutzung die Linie oben mit einem Lineal. Sie muss 50 mm lang sein.",
            "Wenn nicht, gib in neVus ein, was du gemessen hast (Einstellungen > Referenzkarte): Die Messungen werden "
            "korrigiert.",
            "Schneide an der dünnen Kontur entlang und schneide das 24-mm-Fenster aus. Lege das Fenster auf die "
            "Stelle,",
            "flach auf die Haut, und fotografiere von oben. Nimm den Streifen, wo die Karte nicht flach aufliegt.",
            "Glänzendes Papier und glänzende Laminierung erzeugen Reflexe, die die Markierungen verdecken.",
            "Die Karte berührt die Haut: nur persönlich nutzen, mit Alkohol abwischen, bei Abnutzung ersetzen.",
        ],
        "line": "50 mm",
        "spares": "Graue Quadrate für eine 3D-gedruckte Karte: Schneide eines aus und klebe es auf das schwarze "
        "Quadrat der Karte.",
    },
    "nl": {
        "title": "neVus-referentiekaart v1",
        "lines": [
            "Print op 100 % (ware grootte, niet aanpassen aan de pagina) op mat karton of mat fotopapier.",
            "Meet vóór het eerste gebruik de lijn hierboven met een liniaal. Hij moet 50 mm zijn.",
            "Zo niet, voer dan in neVus in wat je gemeten hebt (Instellingen > Referentiekaart): metingen worden "
            "gecorrigeerd.",
            "Knip langs de dunne contour en knip het venster van 24 mm uit. Leg het venster over de plek,",
            "plat op de huid, en fotografeer van bovenaf. Gebruik de strip waar de kaart niet plat kan liggen.",
            "Glanzend papier en glanzende lamineerfolie geven reflecties die de markeringen verbergen.",
            "De kaart raakt de huid: houd hem persoonlijk, veeg hem af met alcohol, vervang hem als hij versleten is.",
        ],
        "line": "50 mm",
        "spares": "Grijze vierkantjes voor een 3D-geprinte kaart: knip er een uit en plak het over het zwarte "
        "vierkant van de kaart.",
    },
    "pl": {
        "title": "Karta referencyjna neVus v1",
        "lines": [
            "Wydrukuj w skali 100 % (rozmiar rzeczywisty, bez dopasowania do strony) na matowym kartonie lub papierze "
            "fotograficznym.",
            "Przed pierwszym użyciem zmierz linię powyżej linijką. Musi mieć 50 mm.",
            "Jeśli nie ma, wpisz w neVus wynik pomiaru (Ustawienia > Karta referencyjna): pomiary zostaną skorygowane.",
            "Wytnij wzdłuż cienkiego konturu i wytnij okno 24 mm. Połóż okno na oznaczeniu,",
            "płasko na skórze, i zrób zdjęcie z góry. Użyj paska tam, gdzie karta nie leży płasko.",
            "Błyszczący papier i błyszcząca laminacja dają odblaski, które zasłaniają znaczniki.",
            "Karta dotyka skóry: używaj jej osobiście, przecieraj alkoholem, wymień, gdy się zużyje.",
        ],
        "line": "50 mm",
        "spares": "Szare kwadraty do karty drukowanej w 3D: wytnij jeden i przyklej na czarny kwadrat karty.",
    },
    "ru": {
        "title": "Эталонная карточка neVus v1",
        "lines": [
            "Печатайте в масштабе 100 % (реальный размер, без подгонки под страницу) на матовом картоне или "
            "фотобумаге.",
            "Перед первым использованием измерьте линейкой линию выше. Она должна быть 50 мм.",
            "Если нет, введите в neVus результат измерения (Настройки > Эталонная карточка): измерения будут "
            "скорректированы.",
            "Вырежьте по тонкому контуру и вырежьте окно 24 мм. Положите окно на метку,",
            "плотно к коже, и снимайте сверху. Используйте полоску там, где карточка не ложится ровно.",
            "Глянцевая бумага и глянцевая ламинация дают блики, скрывающие маркеры.",
            "Карточка касается кожи: пользуйтесь ею лично, протирайте спиртом, меняйте, когда износится.",
        ],
        "line": "50 mm",
        "spares": "Серые квадраты для карточки, напечатанной на 3D-принтере: вырежьте один и наклейте на чёрный "
        "квадрат карточки.",
    },
    "tr": {
        "title": "neVus referans kartı v1",
        "lines": [
            "% 100 ölçekte (gerçek boyut, sayfaya sığdırmadan) mat karton veya mat fotoğraf kâğıdına yazdırın.",
            "İlk kullanımdan önce yukarıdaki çizgiyi cetvelle ölçün. 50 mm olmalıdır.",
            "Değilse, ölçtüğünüz değeri neVus'a girin (Ayarlar > Referans kartı): ölçümler düzeltilir.",
            "İnce kenar boyunca kesin ve 24 mm'lik pencereyi kesip çıkarın. Pencereyi işaretin üzerine,",
            "cilde düz olacak şekilde koyun ve yukarıdan fotoğraflayın. Kart düz durmuyorsa şeridi kullanın.",
            "Parlak kâğıt ve parlak laminasyon, işaretleyicileri gizleyen yansımalara yol açar.",
            "Kart cilde değer: kişisel kalsın, alkolle silin, yıprandığında yenisiyle değiştirin.",
        ],
        "line": "50 mm",
        "spares": "3D yazıcıyla basılan kart için gri kareler: birini kesin ve kartın siyah karesinin üzerine "
        "yapıştırın.",
    },
    "id": {
        "title": "Kartu referensi neVus v1",
        "lines": [
            "Cetak pada 100 % (ukuran asli, tanpa menyesuaikan halaman) di karton matte atau kertas foto matte.",
            "Sebelum dipakai pertama kali, ukur garis di atas dengan penggaris. Panjangnya harus 50 mm.",
            "Jika tidak, masukkan hasil ukuran Anda ke neVus (Pengaturan > Kartu referensi): pengukuran akan "
            "dikoreksi.",
            "Gunting mengikuti garis tepi tipis dan gunting jendela 24 mm. Letakkan jendela di atas tanda,",
            "rata di kulit, lalu foto dari atas. Pakai strip jika kartu tidak bisa rata.",
            "Kertas mengilap dan laminasi mengilap menimbulkan pantulan yang menutupi penanda.",
            "Kartu menyentuh kulit: gunakan sendiri, lap dengan alkohol, ganti jika sudah aus.",
        ],
        "line": "50 mm",
        "spares": "Kotak abu-abu untuk kartu cetak 3D: gunting satu dan tempel di atas kotak hitam kartu.",
    },
    "zh": {
        "title": "neVus 参考卡 v1",
        "lines": [
            "请按 100 %（实际尺寸，不要缩放适应页面）打印在哑光卡纸或哑光相纸上。",
            "首次使用前，用尺子量一量上面的线，它应为 50 毫米。",
            "如果不是，请把量得的数值填入 neVus（设置 > 参考卡）：测量结果会据此校正。",
            "沿细轮廓线剪下，并剪掉 24 毫米的窗口。把窗口盖在标记上，",
            "平贴在皮肤上，从正上方拍照。卡片无法放平的地方，请用长条。",
            "光面纸和光面覆膜会产生反光，遮住定位标记。",
            "卡片会接触皮肤：请专人专用，用酒精擦拭，磨损后更换。",
        ],
        "line": "50 mm",
        "spares": "用于 3D 打印卡片的灰色方块：剪下一块，贴在卡片的黑色方块上。",
    },
    "ja": {
        "title": "neVus リファレンスカード v1",
        "lines": [
            "100 %（実寸、ページに合わせない）で、マットなカードまたはマットな写真用紙に印刷してください。",
            "初めて使う前に、上の線を定規で測ってください。50 mm になるはずです。",
            "違う場合は、測った値を neVus（設定 > リファレンスカード）に入力してください。計測値が補正されます。",
            "細い輪郭線に沿って切り、24 mm の窓を切り抜きます。窓をマークに重ね、",
            "肌に平らに当てて、真上から撮影します。カードが平らにならない場所ではストリップを使います。",
            "光沢紙や光沢ラミネートは反射を起こし、マーカーを隠してしまいます。",
            "カードは肌に触れます：個人専用にし、アルコールで拭き、傷んだら交換してください。",
        ],
        "line": "50 mm",
        "spares": "3Dプリントのカード用のグレーの四角：1枚切り取り、カードの黒い四角の上に貼ります。",
    },
    "ko": {
        "title": "neVus 참조 카드 v1",
        "lines": [
            "100 %(실제 크기, 페이지에 맞추지 않음)로 무광 카드지나 무광 사진용지에 인쇄하세요.",
            "처음 쓰기 전에 위의 선을 자로 재세요. 50 mm여야 합니다.",
            "아니라면 잰 값을 neVus(설정 > 참조 카드)에 입력하세요. 측정값이 보정됩니다.",
            "얇은 윤곽선을 따라 자르고 24 mm 창을 오려 내세요. 창을 표시 위에 대고,",
            "피부에 평평하게 놓고 위에서 촬영하세요. 카드가 평평하게 놓이지 않는 곳에는 띠를 쓰세요.",
            "유광 용지와 유광 코팅은 빛 반사를 일으켜 마커를 가립니다.",
            "카드는 피부에 닿습니다. 본인만 쓰고, 알코올로 닦고, 닳으면 교체하세요.",
        ],
        "line": "50 mm",
        "spares": "3D 프린트 카드용 회색 사각형: 하나를 오려 카드의 검은 사각형 위에 붙이세요.",
    },
    "hi": {
        "title": "neVus संदर्भ कार्ड v1",
        "lines": [
            "100 % पर (वास्तविक आकार, पेज में फ़िट किए बिना) मैट कार्ड या मैट फ़ोटो पेपर पर प्रिंट करें।",
            "पहली बार इस्तेमाल से पहले ऊपर की रेखा को स्केल से नापें। वह 50 mm होनी चाहिए।",
            "अगर नहीं है, तो जो नापा उसे neVus में दर्ज करें (सेटिंग > संदर्भ कार्ड): माप सुधार दिए जाते हैं।",
            "पतली रूपरेखा पर काटें और 24 mm की खिड़की काट लें। खिड़की को निशान पर रखें,",
            "त्वचा पर सपाट, और ऊपर से फ़ोटो लें। जहाँ कार्ड सपाट न टिके, वहाँ पट्टी इस्तेमाल करें।",
            "चमकदार काग़ज़ और चमकदार लैमिनेशन से परावर्तन होता है, जो मार्कर छिपा देता है।",
            "कार्ड त्वचा को छूता है: उसे निजी रखें, अल्कोहल से पोंछें, घिस जाए तो बदल दें।",
        ],
        "line": "50 mm",
        "spares": "3D प्रिंट किए कार्ड के लिए स्लेटी वर्ग: एक काटें और कार्ड के काले वर्ग पर चिपका दें।",
    },
    "ar": {
        "title": "بطاقة neVus المرجعية الإصدار 1",
        "lines": [
            "اطبع بنسبة 100 % (الحجم الحقيقي دون ملاءمة الصفحة) على ورق مقوّى مطفي أو ورق صور مطفي.",
            "قبل أول استخدام، قِس الخط أعلاه بمسطرة. يجب أن يكون طوله 50 mm.",
            "إن لم يكن كذلك، فأدخل ما قسته في neVus (الإعدادات > البطاقة المرجعية): تُصحَّح القياسات.",
            "قصّ على طول الحدود الرفيعة واقطع النافذة بقياس 24 mm. ضع النافذة فوق العلامة،",
            "مسطّحة على الجلد، وصوّر من الأعلى. استخدم الشريط حيث لا تستقر البطاقة مسطّحة.",
            "الورق اللامع والتغليف اللامع يسببان انعكاسات تخفي المؤشرات.",
            "البطاقة تلامس الجلد: اجعلها شخصية، امسحها بالكحول، واستبدلها عند تلفها.",
        ],
        "line": "50 mm",
        "spares": "مربعات رمادية لبطاقة مطبوعة ثلاثية الأبعاد: قصّ مربعًا والصقه فوق المربع الأسود في البطاقة.",
    },
}


class SvgPainter:
    """The Painter protocol into SVG, in millimetres, with y running down the page."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.fill = 0.0
        self.stroke = 0.0
        self.width = 0.3

    @staticmethod
    def _grey(level: float) -> str:
        value = round(max(0.0, min(1.0, level)) * 255)
        return f"#{value:02x}{value:02x}{value:02x}"

    def fill_gray(self, level: float) -> None:
        self.fill = level

    def stroke_gray(self, level: float) -> None:
        self.stroke = level

    def line_width(self, mm: float) -> None:
        self.width = mm

    def _paint(self, fill: bool, stroke: bool) -> str:
        parts = [f'fill="{self._grey(self.fill)}"' if fill else 'fill="none"']
        if stroke:
            parts.append(f'stroke="{self._grey(self.stroke)}" stroke-width="{self.width:g}"')
        return " ".join(parts)

    def rect(self, x: float, y: float, w: float, h: float, *, fill: bool = True, stroke: bool = False) -> None:
        self.parts.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" {self._paint(fill, stroke)}/>')

    def rects(self, boxes: list[tuple[float, float, float, float]]) -> None:
        for x, y, w, h in boxes:
            self.rect(x, y, w, h)

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.parts.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" {self._paint(False, True)}/>')

    def circle(self, cx: float, cy: float, r: float, *, fill: bool = False, stroke: bool = True) -> None:
        self.parts.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" {self._paint(fill, stroke)}/>')

    def text(self, x: float, y: float, text: str, size_mm: float, *, bold: bool = False, align: str = "left") -> None:
        anchor = {"left": "start", "center": "middle", "right": "end"}[align]
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size_mm:g}" font-weight="{600 if bold else 400}" '
            f'text-anchor="{anchor}" fill="{self._grey(self.fill)}">{escape(text)}</text>'
        )

    def svg(self, width: float, height: float) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:g}mm" height="{height:g}mm" '
            f'viewBox="0 0 {width:g} {height:g}">{"".join(self.parts)}</svg>'
        )


def render_sheet(page: str = "a4", lang: str = "en") -> bytes:
    lang = normalise(lang)
    text = TEXT.get(lang, TEXT["en"])
    width, height = PAGES.get(page, PAGES["a4"])
    p = SvgPainter()
    left = (width - 2 * WINDOW.width - 10.0) / 2
    p.text(width / 2, 20.0, text["title"], 5.0, bold=True, align="center")
    for i in range(2):
        draw_card(p, WINDOW, left + i * (WINDOW.width + 10.0), 30.0)
        draw_card(p, STRIP, left + i * (WINDOW.width + 10.0) + (WINDOW.width - STRIP.width) / 2, 95.0)
    # Verification line: the whole sheet is scaled by the same factor, so one line checks every card.
    y = 130.0
    x0 = width / 2 - 25.0
    p.stroke_gray(0.0)
    p.line_width(0.25)
    p.line(x0, y, x0 + 50.0, y)
    p.line(x0, y - 3.0, x0, y + 3.0)
    p.line(x0 + 50.0, y - 3.0, x0 + 50.0, y + 3.0)
    p.fill_gray(0.0)
    p.text(width / 2, y - 4.0, text["line"], 3.0, bold=True, align="center")
    rtl = direction(lang) == "rtl"
    margin, align = (width - left, "right") if rtl else (left, "left")  # running text starts at the reader's side
    for n, line in enumerate(text["lines"]):
        p.text(margin, 145.0 + n * 6.0, line, 3.0, align=align)
    # Spare grey squares for a 3D-printed card, whose own patch comes out black: the window card's 8 mm and
    # the strip's 6 mm, with a hairline to cut along.
    y = 145.0 + len(text["lines"]) * 6.0 + 6.0
    p.text(margin, y, text["spares"], 3.0, align=align)
    p.stroke_gray(0.0)
    p.line_width(0.1)
    x = left
    for size in (WINDOW.grey[2], WINDOW.grey[2], WINDOW.grey[2], STRIP.grey[2], STRIP.grey[2]):
        p.fill_gray(GREY)
        p.rect(x, y + 3.0, size, size, fill=True, stroke=True)
        x += size + 4.0
    html = HTML.format(
        lang=lang,
        dir=direction(lang),
        title=escape(text["title"]),
        width=width,
        height=height,
        svg=p.svg(width, height),
    )
    return pdf_from_html(html)
