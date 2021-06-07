@Echo off
@Rem Python launcher with pause at exit
SetLocal EnableDelayedExpansion
Title %~n0
CD /D "%~dp0"

Python pool_scraper.py
Set ExitCode=!ErrorLevel!
Echo.
If Not "!ExitCode!"=="0" (
    Echo ExitCode: !ExitCode!  1>&2
)
Pause
Exit !ExitCode!