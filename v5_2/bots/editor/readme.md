# Editor

An editor bot received a 3 parts

+ user_message
+ bot_output
+ bot_prompt

The editor generates an improved prompt using its own prompt, and the new prompt
is stored to replace the old.

The original bot will use the newly edited prompt.