import { browser } from 'k6/experimental/browser';
import { check } from 'k6';

export const options = {
    scenarios: {
        ui: {
            executor: 'shared-iterations',
            options: {
                browser: {
                    type: 'chromium',
                },
            },
        },
    },
    thresholds: {
        checks: ["rate==1.0"]
    }
}

export default async function () {
    const context = browser.newContext();
    const page = context.newPage();

    try {
        await page.goto('https://paddock.b4mad.racing');

        await Promise.all([page.waitForNavigation()]);

        check(page, {
            'header': p => p.locator('div.container').textContent() == 'Enable',
        });
    } finally {
        page.close();
    }
}
