import config

please_wait     = config.get_or_default("TextOverrides", "PleaseWait",     "... Please Wait ...")
thats_enough    = config.get_or_default("TextOverrides", "ThatsEnough",    "Alright that's enough")
to_be_continued = config.get_or_default("TextOverrides", "ToBeContinued",  ".... To Be Continued ...")
thinking        = config.get_or_default("TextOverrides", "Thinking",       "Thinking:")
empty_reply     = config.get_or_default("TextOverrides", "EmptyReply",     "[Empty Reply]")
service_refused = config.get_or_default("TextOverrides", "ServiceRefused", "Service refused")