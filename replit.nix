{ pkgs }: {
  deps = [
    pkgs.python310Full
    pkgs.python310Packages.pip
    pkgs.python310Packages.flask
    pkgs.python310Packages.sqlalchemy
    pkgs.python310Packages.beautifulsoup4
    pkgs.python310Packages.requests
    pkgs.python310Packages.python-dateutil
    pkgs.python310Packages.pytz
    pkgs.wkhtmltopdf
  ];
}
