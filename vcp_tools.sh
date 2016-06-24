# -*- mode: shell-script -*-

function vcp_setup_tab_completion {
    _reporitories () {
        local cur="${COMP_WORDS[COMP_CWORD]}"
        COMPREPLY=( $(compgen -W "`vcp repository list --format lines`" -- ${cur}) )
    }

    complete -o default -o nospace -F _reporitories vj
}

function vcp_initialize {
    vcp_setup_tab_completion
}

function vj {
    repo_name="$1"
    path=`vcp repository show_path $1`
    cd $path
}

vcp_initialize
