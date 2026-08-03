---
name: feishu-transcribe
description: Transcribe an audio recording someone sent in chat — a sales call, a voice note, a meeting — and file the transcript into a doc or a CRM record. Use whenever a message carries an audio file (mp3/m4a/wav/aac/amr/opus) or someone asks to 转写/转录/整理 a 录音.
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +update", "docs +media-insert", "drive +member-add"]
---
Transcription is the `transcribe_audio` tool, NOT a feishu_cli command. It takes two
handles and returns text; everything before and after it is ordinary skill work.

RECOGNISING A RECORDING — an audio message renders as two lines:

    <file key="file_v3_0013v_…" name="20260420_105107.mp3"/>
    [attachment message_id=om_x100b… file_key=file_v3_0013v_… type=file]

`type=file` is Feishu's storage bucket, not the media kind — the kind is the tag and the
extension. Audio extensions: mp3, m4a, wav, aac, amr, opus, ogg.

COPY BOTH HANDLES OUT OF THE MESSAGE THE MOMENT YOU SEE THEM. They exist only in this
turn's raw text: tool arguments are squeezed to 60 characters when the turn is stored,
and older turns are deleted outright when the context folds. A `file_key` you did not
copy is gone — it cannot be guessed, reconstructed, or found by listing the chat
(that listing is unreliable: the same call returns the file message once and not the
next time).

ALWAYS RUN IT AS A BACKGROUND TASK. A recording takes tens of seconds to minutes; the
person must not sit watching a spinner. Tell them it has started, then:

    run_in_background(
      title="逐字稿 20260420_105107.mp3",
      goal="Transcribe the recording sent in this chat and file it into a doc.
            message_id=om_x100b696247f8d8a0c020bb147303010
            file_key=file_v3_0013v_191bdb2d-…
            file_name=20260420_105107.mp3
            Call transcribe_audio ONCE with exactly those three values, then create the
            doc, share it with the requester, and report the summary.")

Write the ids INTO the goal literally, and put the file name in the title. Two reasons,
both of which bite silently:
- the task carries no attachment of its own, so the goal is the only place the handles
  can travel to the background run;
- two tasks with the same title and goal in the same minute are collapsed into one. A
  rep who sends two recordings back to back would lose the second, and the tool would
  answer "an identical task is already queued" — which reads like success. The ids are
  unique per recording, so writing them in makes the two tasks distinct for free.

IN THE BACKGROUND RUN — call it once:

    transcribe_audio(message_id="om_…", file_key="file_v3_…", file_name="…mp3")

- `language` stays empty. Detection is reliable (a Cantonese/Mandarin/English call was
  identified as Chinese at 0.998 with no hint). Pass it only to correct a wrong guess.
- NEVER call it twice for one recording. Every call downloads and pays for the audio
  again. If the reply starts "Transcription failed", report that sentence to the person
  and stop — do not retry, do not try another route, and never narrate a transcript you
  did not receive.
- Use the transcript in the SAME run: summarise it and write the doc immediately. It is
  in front of you now and will be a 200-character digest by the next turn.

WHAT COMES BACK — a header line, then the dialogue:

    duration=12:23 language=zho speakers=agent,customer chars=5574

    [00:02] agent: …
    [00:11] customer: …

`agent`/`customer` are the transcription model's own role detection, and they arrive in
English whatever language the call was in. **Translate them when you write the doc or the
reply** — 销售/客户 for a Chinese-speaking team — the same way you translate everything
else you say. When roles could not be resolved the labels are `speaker_0`/`speaker_1`
instead; keep them numbered rather than guessing who is who.

A recording of one voice, or a call captured on a single channel, collapses into one
speaker — that is the audio, not a bug; say so rather than inventing a second party.

FILE IT — read_skill("feishu-docs") for the DocxXML grammar and the chunking rule; this
skill does not repeat them. Title the doc for the customer and the date, e.g.
`[通话逐字稿] 客户名 2026-04-20`. Never build the title out of the raw file name.
The HARD RULE from feishu-docs applies unchanged: share it with the requester via
`drive +member-add` in the same turn as the create, before you report back.

For a CRM row instead of a doc, read_skill("feishu-base") — the transcript goes in a
text field, the doc link in a URL field.

IF THE OUTPUT SAYS [TRUNCATED — the call was longer than fits in one reply. The tool
writes the complete transcript to a local file and names it. Then:
1. create the doc with the part you have,
2. attach the complete file to it:
   ["docs", "+media-insert", "--doc", "<doc id>", "--file", "./hl-transcript-….txt",
    "--type", "file", "--file-view", "preview"]
3. put the truncation warning at the top of the doc AND in your reply. A half-filed
   transcript that reads as complete is worse than no transcript at all.
Never retype the transcript to work around truncation — the file is there so the bytes
never have to pass through you.

REPLY WITH: the doc link, duration, language, who spoke, and three bullets of substance
— what the customer asked for, what they objected to, what happens next. Never paste the
transcript into the chat.

IN A GROUP CHAT the bot cannot see a file that was not addressed to it. The recording is
held for ten minutes and only the last five files: tell the rep to send the recording and
then @-mention the bot right away. In a 1:1 no mention is needed.

This skill covers audio files. A Feishu VOICE message (hold-to-talk) is not supported
yet — say so plainly and ask for the recording as a file instead.
