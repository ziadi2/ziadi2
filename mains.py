import flet as ft
from datetime import datetime

def main(page: ft.Page):
    page.title = "حاسبة العمر"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.bgcolor = "#f0f8ff"  # لون خلفية فاتح
    
    # إطار رئيسي للتطبيق
    main_container = ft.Container(
        width=400,
        padding=20,
        border_radius=15,
        bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.BLUE_GREY_300,
            offset=ft.Offset(0, 0),
        ),
    )
    
    # عنوان التطبيق
    title = ft.Text(
        "حاسبة العمر",
        size=28,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.BLUE_800,
        text_align= ft.TextAlign.CENTER,
    )
    
    # حقول إدخال تاريخ الميلاد
    day_field = ft.TextField(
        label="اليوم",
        width=100,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    
    month_field = ft.TextField(
        label="الشهر",
        width=100,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    
    year_field = ft.TextField(
        label="السنة",
        width=100,
        text_align=ft.TextAlign.CENTER,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    
    # حقل تاريخ الميلاد (للاختيار من التقويم)
    date_field = ft.DatePicker(
        first_date=datetime(1900, 1, 1),
        last_date=datetime.now(),
        value=datetime.now(),
        on_change=lambda _: update_fields_from_date()
    )
    
    date_button = ft.ElevatedButton(
        "اختر من التقويم",
        icon=ft.Icons.CALENDAR_TODAY,
        on_click=lambda _: date_field.pick_date(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_600,
        ),
    )
    
    # زر حساب العمر
    calculate_button = ft.ElevatedButton(
        "احسب العمر",
        icon=ft.Icons.CALCULATE,
        on_click=lambda _: calculate_age(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_600,
        ),
    )
    
    # نتيجة العمر
    age_result = ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "عمرك هو:",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_700,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.BLUE_900,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=15,
        border_radius=10,
        bgcolor=ft.Colors.BLUE_50,
        border=ft.border.all(2, ft.Colors.BLUE_200),
    )
    
    # دالة تحديث الحقول عند اختيار تاريخ من التقويم
    def update_fields_from_date():
        if date_field.value:
            day_field.value = str(date_field.value.day)
            month_field.value = str(date_field.value.month)
            year_field.value = str(date_field.value.year)
            page.update()
    
    # دالة حساب العمر
    def calculate_age():
        try:
            day = int(day_field.value)
            month = int(month_field.value)
            year = int(year_field.value)
            
            birth_date = datetime(year, month, day)
            today = datetime.now()
            
            years = today.year - birth_date.year
            months = today.month - birth_date.month
            days = today.day - birth_date.day
            
            if days < 0:
                months -= 1
                days += 30  # تقريبًا
            
            if months < 0:
                years -= 1
                months += 12
            
            age_result.content.controls[1].value = f"{years} سنة، {months} شهر، {days} يوم"
            page.update()
        except (ValueError, AttributeError):
            age_result.content.controls[1].value = "الرجاء إدخال تاريخ صحيح"
            page.update()
    
    # محتوى التطبيق
    content = ft.Column(
        [
            title,
            ft.Divider(height=20, color=ft.Colors.BLUE_200),
            ft.Row(
                [day_field, month_field, year_field],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            ft.Divider(height=10, color=ft.Colors.BLUE_200),
            date_button,
            ft.Divider(height=10, color=ft.Colors.BLUE_200),
            calculate_button,
            ft.Divider(height=20, color=ft.Colors.BLUE_200),
            age_result,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    
    main_container.content = content
    page.add(main_container)

ft.app(target=main)
