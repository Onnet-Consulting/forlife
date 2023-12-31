#!/usr/bin/env bash
set -Eeuo pipefail

declare -A aliases=(
	[13]='latest'
	[9.6]='9'
)

self="$(basename "$BASH_SOURCE")"
cd "$(dirname "$(readlink -f "$BASH_SOURCE")")"

if [ "$#" -eq 0 ]; then
	versions="$(jq -r 'keys | map(@sh) | join(" ")' versions.json)"
	eval "set -- $versions"
fi

# sort version numbers with highest first
IFS=$'\n'; set -- $(sort -rV <<<"$*"); unset IFS

# get the most recent commit which modified any of "$@"
fileCommit() {
	git log -1 --format='format:%H' HEAD -- "$@"
}

# get the most recent commit which modified "$1/Dockerfile" or any file COPY'd from "$1/Dockerfile"
dirCommit() {
	local dir="$1"; shift
	(
		cd "$dir"
		files="$(
			git show HEAD:./Dockerfile | awk '
				toupper($1) == "COPY" {
					for (i = 2; i < NF; i++) {
						if ($i ~ /^--from=/) {
							next
						}
						print $i
					}
				}
			'
		)"
		fileCommit Dockerfile $files
	)
}

getArches() {
	local repo="$1"; shift
	local officialImagesUrl='https://github.com/docker-library/official-images/raw/master/library/'

	eval "declare -g -A parentRepoToArches=( $(
		find -name 'Dockerfile' -exec awk '
				toupper($1) == "FROM" && $2 !~ /^('"$repo"'|scratch|.*\/.*)(:|$)/ {
					print "'"$officialImagesUrl"'" $2
				}
			' '{}' + \
			| sort -u \
			| xargs bashbrew cat --format '[{{ .RepoName }}:{{ .TagName }}]="{{ join " " .TagEntry.Architectures }}"'
	) )"
}
getArches 'postgres'

cat <<-EOH
# this file is generated via https://github.com/docker-library/postgres/blob/$(fileCommit "$self")/$self

Maintainers: Tianon Gravi <admwiggin@gmail.com> (@tianon),
             Joseph Ferguson <yosifkit@gmail.com> (@yosifkit)
GitRepo: https://github.com/docker-library/postgres.git
EOH

# prints "$2$1$3$1...$N"
join() {
	local sep="$1"; shift
	local out; printf -v out "${sep//%/%%}%s" "$@"
	echo "${out#$sep}"
}

for version; do
	export version

	variants="$(jq -r '.[env.version].debianSuites + ["alpine"] | map(@sh) | join(" ")' versions.json)"
	eval "variants=( $variants )"

	debian="$(jq -r '.[env.version].debian' versions.json)"

	fullVersion="$(jq -r '.[env.version].version' versions.json)"
	origVersion="$fullVersion"

	versionAliases=()
	while [ "$fullVersion" != "$version" -a "${fullVersion%[.-]*}" != "$fullVersion" ]; do
		versionAliases+=( $fullVersion )
		fullVersion="${fullVersion%[.-]*}"
	done
	# skip unadorned "version" on prereleases: https://www.postgresql.org/developer/beta/
	# - https://github.com/docker-library/postgres/issues/662
	# - https://github.com/docker-library/postgres/issues/784
	case "$origVersion" in
		*alpha* | *beta* | *rc*) ;;
		*) versionAliases+=( $version ) ;;
	esac
	versionAliases+=(
		${aliases[$version]:-}
	)

	for variant in "${variants[@]}"; do
		dir="$version/$variant"
		commit="$(dirCommit "$dir")"

		parent="$(awk 'toupper($1) == "FROM" { print $2 }' "$dir/Dockerfile")"
		arches="${parentRepoToArches[$parent]}"

		variantAliases=( "${versionAliases[@]/%/-$variant}" )
		variantAliases=( "${variantAliases[@]//latest-/}" )

		if [ "$variant" = "$debian" ]; then
			variantAliases=(
				"${versionAliases[@]}"
				"${variantAliases[@]}"
			)
		fi

		echo
		cat <<-EOE
			Tags: $(join ', ' "${variantAliases[@]}")
			Architectures: $(join ', ' $arches)
			GitCommit: $commit
			Directory: $dir
		EOE
	done
done
