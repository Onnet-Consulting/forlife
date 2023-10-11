/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { companyService } from '@web/webclient/company_service';
import { symmetricalDifference } from "@web/core/utils/arrays";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";

function parseCompanyIds(cidsFromHash) {
    const cids = [];
    if (typeof cidsFromHash === "string") {
        cids.push(...cidsFromHash.split(",").map(Number));
    } else if (typeof cidsFromHash === "number") {
        cids.push(cidsFromHash);
    }
    return cids;
}

function computeAllowedCompanyIds(cids) {
    const {user_companies} = session;
    let allowedCompanyIds = cids || [];
    const availableCompaniesFromSession = user_companies.allowed_companies;
    const notReallyAllowedCompanies = allowedCompanyIds.filter(
        (id) => !(id in availableCompaniesFromSession)
    );

    if (!allowedCompanyIds.length || notReallyAllowedCompanies.length) {
        allowedCompanyIds = [user_companies.current_company];
    }
    return allowedCompanyIds;
}

patch(companyService, "x_company", {
    start(env, {user, router, cookie}) {
        let cids;
        if ("cids" in router.current.hash) {
            cids = parseCompanyIds(router.current.hash.cids);
        } else if ("cids" in cookie.current) {
            cids = parseCompanyIds(cookie.current.cids);
        }
        const allowedCompanyIds = computeAllowedCompanyIds(cids);

        const stringCIds = allowedCompanyIds.join(",");
        router.replaceState({cids: stringCIds}, {lock: true});
        cookie.setCookie("cids", stringCIds);

        user.updateContext({allowed_company_ids: allowedCompanyIds});
        const availableCompanies = session.user_companies.allowed_companies;

        return {
            availableCompanies,
            get allowedCompanyIds() {
                return allowedCompanyIds.slice();
            },
            get currentCompany() {
                return availableCompanies[allowedCompanyIds[0]];
            },
            setCompanies(mode, ...companyIds) {
                // compute next company ids
                let nextCompanyIds;
                if (mode === "toggle") {
                    nextCompanyIds = symmetricalDifference(allowedCompanyIds, companyIds);
                } else if (mode === "loginto") {
                    const companyId = companyIds[0];
                    if (allowedCompanyIds.length === 1) {
                        // 1 enabled company: stay in single company mode
                        nextCompanyIds = [companyId];
                    } else {
                        // multi company mode
                        nextCompanyIds = [
                            companyId,
                            ...allowedCompanyIds.filter((id) => id !== companyId),
                        ];
                    }
                }
                nextCompanyIds = (nextCompanyIds.length && session.is_system) ? nextCompanyIds : [companyIds[0]];

                // apply them
                router.pushState({cids: nextCompanyIds}, {lock: true});
                cookie.setCookie("cids", nextCompanyIds);
                browser.setTimeout(() => browser.location.reload()); // history.pushState is a little async
            },
        };
    },
})