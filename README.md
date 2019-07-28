# AppMonitor

### A Discord bot for monitoring iOS AppStore applications. DM’s you when an application you’re monitoring has received an update!

Invite to your server: https://discordapp.com/oauth2/authorize?client_id=593029590205726735&scope=bot&permissions=8

***

#### TABLE OF CONTENTS (COMMANDS)
* Watch-List
* Search
* Add
* Update
* Remove
* Help
* More
* Source


#### WATCH-LIST
Each user has their own “watch-list”, a track list where the user’s applications will be managed through. This list contains all the user’s application and can only be managed by the corresponding user. The user can add, remove and update this list. A maximum of 50 applications is allowed per user.

Running the command will send a message with all the applications in the watch-list listed, along with their bundle identifier, version, name and status (up-to-date or outdated). The color of the message will be green if all the applications are up-to-date, and orange if there’s an application that is not. The list can be sorted using “name”, “bundle_id” or “version” as sort key. Passing the parameter "o" or "outdated" will yield a list with only the outdated applications.

Usage: `.watch-list *<sort key> .. OR .. *outdated`

![](https://i.imgur.com/MES9HCr.png)


#### SEARCH
Users can search the AppStore for applications. The country version of the AppStore may also be specified. A message with information about the first matching application will be sent. This information will contain the applications name, publisher, version, update date, price, rating, icon and bundle identifier. The search result can then be added directly to the users watch-list.

Usage: `.search <string> *<country>`

![](https://i.imgur.com/he7WLlC.png)

### ADD
Users can add applications to their watch-list using the applications bundle identifier. The user may also specify which country version of the AppStore they want the application’s information to be gathered and monitored from. Multiple applications can be added at once by separating the bundle identifiers with a whitespace.

Usage: `.add <bundle identifier> *<bundle identifier> … *<country>`

![](https://i.imgur.com/8YuMfyB.png)

#### UPDATE
Users can update the version of the application in their watch-list to the latest version available, making the application up-to-date in the watch-list.

Usage: `.update <bundle identifier>`

![](https://i.imgur.com/nSg92zn.png)


#### REMOVE
Users can remove applications from their watch-list using the applications bundle identifier.

Usage: `.remove <bundle identifier>`

https://i.imgur.com/qtdVNKI.png


#### HELP
A list of all the commands available to the command issuer will be sent with a brief description of each command.

Usage: `.help`

![](https://i.imgur.com/forXAIt.png)


#### MORE
A message containing more information about the specified command will be sent. This information contains aliases, a description and the usage syntax for the command.

Usage: `.more <command>`

![](https://i.imgur.com/LP0XrLq.png)

#### SOURCE
A message with information about this bot and its author will be sent.

Usage: `.source`

![](https://i.imgur.com/dHOWQgd.png)


###### * OPTIONAL ARGUMENT


Available at https://kevinissa.dev/appmonitor.html.

![gif](https://i.imgur.com/zagrBxu.gif)
