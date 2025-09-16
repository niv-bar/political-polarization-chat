import os
import csv
from pathlib import Path


def convert_csv_to_utf8_bom(input_dir="conversations", output_dir="conversations_fixed"):
    """
    המרת כל קבצי ה-CSV מ-UTF-8 ל-UTF-8 עם BOM
    """
    # יצירת תיקיית פלט אם לא קיימת
    os.makedirs(output_dir, exist_ok=True)

    # ספירת קבצים
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]

    if not csv_files:
        print(f"לא נמצאו קבצי CSV בתיקייה {input_dir}")
        return

    print(f"נמצאו {len(csv_files)} קבצי CSV להמרה")
    print("-" * 50)

    success_count = 0
    error_count = 0

    for csv_file in csv_files:
        input_path = os.path.join(input_dir, csv_file)
        output_path = os.path.join(output_dir, csv_file)

        try:
            # קריאת הקובץ הקיים
            with open(input_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # כתיבה מחדש עם UTF-8 BOM
            with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)

            print(f"✅ {csv_file} - הומר בהצלחה")
            success_count += 1

        except Exception as e:
            print(f"❌ {csv_file} - שגיאה: {e}")
            error_count += 1

    print("-" * 50)
    print(f"סיכום: {success_count} קבצים הומרו בהצלחה, {error_count} שגיאות")

    if success_count > 0:
        print(f"\nהקבצים המומרים נשמרו בתיקייה: {output_dir}")
        print("כעת אפשר לפתוח אותם באקסל והעברית תוצג כראוי!")


def convert_in_place(directory="conversations", backup=True):
    """
    המרה של הקבצים באותה תיקייה (עם אפשרות לגיבוי)
    """
    csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]

    if not csv_files:
        print(f"לא נמצאו קבצי CSV בתיקייה {directory}")
        return

    print(f"נמצאו {len(csv_files)} קבצי CSV להמרה")

    # יצירת תיקיית גיבוי אם נדרש
    if backup:
        backup_dir = f"{directory}_backup"
        os.makedirs(backup_dir, exist_ok=True)
        print(f"יוצר גיבוי בתיקייה: {backup_dir}")

    print("-" * 50)

    for csv_file in csv_files:
        file_path = os.path.join(directory, csv_file)

        try:
            # קריאת הקובץ
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            # גיבוי אם נדרש
            if backup:
                backup_path = os.path.join(backup_dir, csv_file)
                with open(backup_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)

            # כתיבה מחדש עם BOM
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(rows)

            print(f"✅ {csv_file} - הומר בהצלחה")

        except Exception as e:
            print(f"❌ {csv_file} - שגיאה: {e}")

    print("-" * 50)
    print("ההמרה הסתיימה!")
    if backup:
        print(f"הקבצים המקוריים גובו בתיקייה: {backup_dir}")


if __name__ == "__main__":
    # אפשרות 1: המרה לתיקייה חדשה
    # convert_csv_to_utf8_bom(
    #     input_dir="conversations",  # התיקייה עם הקבצים המקוריים
    #     output_dir="conversations_fixed"  # תיקייה חדשה לקבצים המומרים
    # )

    # אפשרות 2: המרה באותה תיקייה (עם גיבוי אוטומטי)
    convert_in_place(
        directory="conversations",
        backup=True  # יוצר גיבוי של הקבצים המקוריים
    )