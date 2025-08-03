import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def imports():
    import marimo as mo
    import datetime
    from civicsignal.ingest.archives import (
        SanFranciscoArchiveParser,
        SanFranciscoArchiveSource,
    )
    from civicsignal.chat import (
        marimo_chat, 
        ChatMessage,
    )
    from civicsignal.transform.embed_meeting import MeetingRAGDb

    ragdb = MeetingRAGDb()
    return (
        SanFranciscoArchiveParser,
        SanFranciscoArchiveSource,
        datetime,
        marimo_chat,
        mo,
        ragdb,
    )


@app.cell(hide_code=True)
def header(mo):
    mo.md(
        """
    # **CivicSignal**
    Welcome to CivicSignal! You're helpful interface to the world of San Francisco politics!
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
def embed_compute(date_dropdown, datetime, embed_button, parser, ragdb):
    def embed_meeting(date_str: str):
        date = datetime.date.fromisoformat(date_str)
        meeting = parser.get_meeting_transcript(date)
        ragdb.embed_meeting(meeting=meeting)

    if embed_button.value:
        embed_meeting(date_str=date_dropdown.value)
    return


@app.cell(hide_code=True)
def civicsignal_chat(marimo_chat, mo):
    mo.ui.chat(
        marimo_chat(),
        prompts=[
            "Tell me about planning meetings",
            "What's going on with the valencia bike lane?",
        ]
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
