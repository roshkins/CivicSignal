#!/usr/bin/env -S marimo run
# /// script
# [tool.marimo.display]
# theme = "dark"
# ///

import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium", layout_file="layouts/app.grid.json")


@app.cell(hide_code=True)
def imports():
    import marimo as mo
    import datetime
    from civicsignal.ingest.archives import (
        SanFranciscoArchiveParser,
        SanFranciscoArchiveSource,
    )
    from civicsignal.chat import (
        CivicSignalChat, 
        ChatMessage,
    )
    from civicsignal.transform.embed_meeting import MeetingRAGDb

    ragdb = MeetingRAGDb()
    return (
        CivicSignalChat,
        SanFranciscoArchiveParser,
        SanFranciscoArchiveSource,
        datetime,
        mo,
        ragdb,
    )


@app.cell(hide_code=True)
def header(mo):
    mo.md(
        """
    # **CivicSignal**
    Welcome to CivicSignal! Your helpful interface to the world of San Francisco politics!
    """
    )
    return


@app.cell(hide_code=True)
def group_picker(SanFranciscoArchiveSource, mo):
    source_dropdown = mo.ui.dropdown(options=[source.name for source in SanFranciscoArchiveSource],value=SanFranciscoArchiveSource.BOARD_OF_SUPERVISORS.name)

    mo.md(f"""
    If you'd like to add more data to the db, select a group {source_dropdown}
    """)
    return (source_dropdown,)


@app.cell(hide_code=True)
def date_picker(
    SanFranciscoArchiveParser,
    SanFranciscoArchiveSource,
    mo,
    source_dropdown,
):
    source = SanFranciscoArchiveSource.from_string(source_dropdown.value)
    parser = SanFranciscoArchiveParser(source)

    all_dates = [date.isoformat() for date in parser.all_meeting_dates()]
    most_recent = parser.last_meeting_date().isoformat()

    date_dropdown = mo.ui.dropdown(options=all_dates, value=most_recent)

    mo.md(f"""
    And then select a date {date_dropdown}""")
    return date_dropdown, parser


@app.cell(hide_code=True)
def embed_button(mo):

    embed_button = mo.ui.run_button(
        label="Embed Meeting",
    )

    mo.md(f"""
    And then wait a bit for some AI magic

    {embed_button}""")
    return (embed_button,)


@app.cell(hide_code=True)
def embed_compute(date_dropdown, datetime, embed_button, mo, parser, ragdb):
    def embed_meeting(date_str: str):
        date = datetime.date.fromisoformat(date_str)
        with mo.status.spinner(title="Embedding meeting...") as _spinner:
            _spinner.update(subtitle="Getting meeting transcript...")
            meeting = parser.get_meeting_transcript(date)
            _spinner.update(subtitle="Embedding transcript into DB...")
            ragdb.embed_meeting(meeting=meeting)

    db_size = ragdb.collection.count()
    display = mo.md(f"Current size of database: {db_size} paragraphs")

    embeding_failed = False
    if embed_button.value:
        embeding_failed = False
        try:
            embed_meeting(date_str=date_dropdown.value)
        except Exception as e:
            embeding_failed = True
            display = mo.md(f"Failed to embed meeting: {e}")

    display
    return


@app.cell(hide_code=True)
def civicsignal_chat(CivicSignalChat, mo):
    # TODO: Add a input field for API key
    model = CivicSignalChat()
    chat = mo.ui.chat(
        model,
        prompts=[
            "Tell me about planning meetings",
            "What's going on with the valencia bike lane?",
        ]
    )
    scrollable_chat = mo.Html(f"""
    <div style="height: 60vh; overflow-y: auto; border: 1px solid #ccc; border-radius: 5px; padding: 10px;">
        {chat}
    </div>
    """)
    mo.output.replace(scrollable_chat)
    return chat, model


@app.cell
def _(chat, mo, model):
    _ = chat.value
    video_height = 720
    video_width = video_height / 1.5
    video_source = model.reference_video_url

    if video_source:
        video_display = mo.video(src=video_source, height=video_height, width=video_width, rounded=True)
    else:
        # just empty space
        video_display = mo.md("")

    video_display
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
