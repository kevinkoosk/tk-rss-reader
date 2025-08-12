# TKinter RSS Reader for Desktop

1. Made with Tkinter (Python) with vibe coding.
2. Binaries available for Windows.

## Description

This is a simple desktop RSS reader made using TKinter (Python).

It can refresh the feeds periodically. (I set the refresh interval at 30 minutes.)

You can export the news articles, and put them into your newsletter or blog as a reading list.

You can also save the news articles for later.

I was inspired by Cryptopanic.com, which aggregates RSS feeds from many websites.

## Features

1. Can specify your preferred RSS feeds
2. Can specify how many days to keep the feed.
3. Can select news items to export to markdown.
4. Can save selected news items.
5. Can specify refresh interval.

## How it works

1. When it launches, it will create an SQLite database in the directory it is launched from. (That's where your settings are saved to.)
2. Please launch it from the same directory, so that it can load up the settings from the database.
3. If you launch it from another directory, it won't be able to see your database. Then you won't be able to see the feed that you've customized.
