# TT-RSS Demo Video — Walkthrough Transcript

**Duration:** ~21 minutes 57 seconds  
**Purpose:** Reference record of the original PHP TT-RSS application behaviour, used as ground truth for migration acceptance.

---

## Transcript

**[00:00]** Hello everyone!

**[00:04]** In this video we'll be talking about Tiny Tiny RSS. It is a self-hosted web application that aggregates RSS or Atom feeds, allowing users to subscribe to news, blogs and podcasts and read them in one place with filtering and tagging.

**[00:37]** For accessing for the first time, we will use the default admin account and default profile.

**[00:49]** Once you are logged in, on the left pane you will find your feed categories and subscriptions. The main area displays your articles, which you can quickly toggle between read and unread posts.

---

### RSS Overview

**[01:13]** What actually RSS is — RSS stands for Really Simple Syndication and the current implementation version of this stack is 2.0.

**[01:26]** RSS consists of two components: RSS readers and RSS feeds. Feeds are actually what you will subscribe to. They are just XML files that a lot of websites have that can be read by the feed reader.

**[01:47]** It contains all articles, videos, posts from source, and the reader displays them in whatever order you choose.

**[02:02]** When a website publishes new articles, the feed updates and the reader gets the new stuff and displays it for the user.

---

### Subscribing to Feeds

**[02:17]** To add a new feed, just open a website you are interested in and look for an icon with an RSS feed — it looks like this.

**[02:42]** Copy the address of such an icon, and in the TT-RSS application, click on the Actions drop-down menu and select "Subscribe to feed" item.

**[03:08]** Paste the copied link address into the URL field and click the Subscribe button.

**[03:22]** Let's add another feed.

**[03:49]** After some time, feeds with articles for the last 24 hours will be displayed in the folder "Uncategorized."

---

### Organizing Feeds with Categories

**[04:04]** We can organize them into categories and tag them for fast navigation. To create a category, click the Actions drop-down menu and select Preferences.

**[04:18]** Then click on the Feeds tab and then click on the Categories drop-down menu to add a category.

**[04:36]** Let's add the title "Tag" and click the button. Category named "Tag" is created.

**[04:53]** Let's add another category called "News." We now have two newly added categories.

**[05:14]** To assign a feed to a category, we need to drag and drop it into the desired category folder.

**[05:36]** Then click "Exit Preferences."

**[05:44]** Now we can see how our feeds are located in the specific category folders: News and Tag.

---

### Editing Feeds

**[05:58]** To edit a feed, select the feed, click Actions, and select "Edit this feed." We can change any of the available fields here, for example the feed title. Then click the Save button and the changes will apply.

---

### Starring and Reading Articles

**[06:41]** While viewing articles, we can mark some of them as starred by clicking on the star icon. Then they appear in the "Starred articles" folder.

**[07:28]** Moving through articles, they become read automatically.

**[07:45]** We can also mark an item as read or unread manually. Select the desired articles and choose the option from the filtering drop-down menu.

---

### Removing a Feed

**[08:25]** To remove a feed, select the feed, right-click, and select "Edit feed" from the drop-down context menu. Click the alert window. The feed will be removed with all its content.

---

### Background Feed Updates

**[08:59]** TT-RSS uses a background process to update feeds automatically at regular intervals. Typically it's a cron job or daemon. By default this interval is set to 7 minutes but can be changed.

**[09:25]** Now let's change it to 15 minutes. After changes, click "Save configuration."

**[09:49]** Hovering the mouse pointer on a feed, we can see the time of the last feed update.

**[10:15]** We can also force a feed update by clicking on the feed title.

---

### Tags

**[10:23]** All articles from all feeds are collected in the "All articles" folder. For fastest search of articles we can use tags.

**[10:30]** Some articles might already have tags. And some of them do not have any tags.

**[10:53]** Click on the plus sign button and add tags separated by commas. Click the Save button.

**[11:14]** We can then select articles which should be displayed by clicking on a tag name.

**[12:06]** We can also use "Select by tag" option from the Actions menu. For example, I selected "Linux kernel" keyword and I can see an article which contains "Linux kernel."

---

### Filters

**[12:26]** We can also create filters to auto-tag articles. For example, create a filter to tag all articles with "Google" as a tag.

**[12:44]** Go to Preferences, click on the Filters tab, click "Create filter." Let's create a filter with a caption. Add a new rule and apply an action.

**[13:42]** This is tested. We can see that two articles are tagged.

**[14:01]** One filter is created. Exit Preferences.

**[14:23]** We can also create filters to auto-mark articles as read, or auto-delete based on keywords.

---

### Multi-User Support

**[14:28]** We can host the TT-RSS application for multiple users, each with their own feed list, preferences, and filters.

**[14:37]** In Actions → Preferences, choose the Users tab and create a new user.

**[15:07]** And try to log in with another user.

**[15:37]** Log out and log in as admin.

---

### OPML Import / Export

**[16:01]** If we need to migrate feeds from another reader or back up, then you can use OPML import and export. OPML files are a universal format supported by nearly every RSS reader.

**Steps for Export:**
**[16:40]** Go to Preferences, click on the Feeds tab, click "Export OPML." Save the OPML file locally.

**Steps for Import:**
**[17:05]** To import OPML, click "Import my OPML file" by choosing the file first. Everything has been imported.

---

### Technical Notes / Deployment

**[18:03]** Tiny Tiny RSS is written in PHP and works with PostgreSQL or MySQL database. You can deploy it on any Linux-based server manually or using Docker.

**[18:24]** In my case, application is running as a Docker container.

**[18:43]** Installation of TT-RSS application is quite easy. Clone the GitHub master branch and run `docker compose up` command.

**[19:44]** OK, let's install it from scratch. Clone the repo, copy `.env` example to `.env`, add Docker config.

**[20:32]** It will take a while.

**[21:27]** Now application is up and running.

**[21:51]** And then — done! Thanks for attention.

---

## Key Observations for Migration

| Feature | PHP Behaviour Observed |
|---------|----------------------|
| Login | Default admin account; session-based auth |
| Feed subscription | Actions menu → Subscribe to feed → URL field |
| Categories | Created in Preferences → Feeds → Categories; feeds assigned by drag-and-drop |
| Feed editing | Right-click or Actions → Edit this feed |
| Starring | Star icon per article; "Starred articles" virtual feed |
| Read/Unread | Auto-mark on scroll; manual toggle via filter dropdown |
| Tags | Plus button on article; comma-separated; filterable by tag |
| Filters | Preferences → Filters → Create filter; regex rules + actions (tag/mark read/delete) |
| Multi-user | Preferences → Users tab; each user has isolated feeds/prefs/filters |
| OPML | Preferences → Feeds → Export OPML / Import OPML |
| Background updates | Cron/daemon; default 7 min; configurable; hover tooltip shows last update time |
| Deployment | PHP + PostgreSQL/MySQL; Docker via `docker compose up` |
| Feed removal | Right-click → Edit feed → delete; removes all content |
