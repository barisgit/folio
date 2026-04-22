from folio.dsl import page, rect, render, tokens

T = tokens.STYLES


def build():
    return render(
        page(
            rect("cover_bg", 0, 0, tokens.A4_WIDTH_MM, tokens.A4_HEIGHT_MM, fill=tokens.INK),
            T.hero("cover_title", 20, 40, "folio", size_pt=28),
            T.hero_subtitle(
                "cover_subtitle",
                20,
                50,
                "Python DSL starter page",
                fill="#d1d8e2",
                fill_opacity=1,
            ),
            page_id="cover",
            filename="cover.svg",
            page_number=1,
        ),
        page(
            rect("notes_bg", 0, 0, tokens.A4_WIDTH_MM, tokens.A4_HEIGHT_MM, fill="#ffffff"),
            T.page_title("notes_title", 20, 32, "Notes", size_pt=20, weight=700),
            T.body.multiline(
                "notes_body",
                20,
                42,
                [
                    "Edit config/folio.py",
                    "or pass another spec file",
                    "to folio build.",
                ],
                line_step_mm=4.5,
                size_pt=11,
                fill=tokens.INK_2,
            ),
            page_id="notes",
            filename="notes.svg",
            page_number=2,
        ),
    )
