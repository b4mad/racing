import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
    stages: [
        { duration: '5m', target: 100 }, // traffic ramp-up from 1 to 100 users over 5 minutes.
        { duration: '30m', target: 100 }, // stay at 100 users for 30 minutes
        { duration: '5m', target: 0 }, // ramp-down to 0 users
    ],
};

export default function Homepage() {
    const params = {
        'sec-ch-ua': '"Chromium";v="94", "Google Chrome";v="94", ";Not A Brand";v="99"',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-GB,en;q=0.9',
    };

    // 01. Go to the homepage
    let responses = http.batch([
        ['GET', 'https://paddock.b4mad.racing/', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/fontawesome.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/brands.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/solid.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/logo-main-black.png', params],
    ]);
    check(responses, {
        'Paddock homepage loaded': (r) => JSON.stringify(r).includes('#B4mad Racing Paddock'),
    });

    sleep(3);

    // 02. Login via Discord
    responses = http.batch([
        ['GET', 'https://paddock.b4mad.racing/accounts/discord/login/', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/fontawesome.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/brands.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/fontawesomefree/css/solid.css', params],
        ['GET', 'https://paddock.b4mad.racing/static/logo-main-black.png', params],

    ]);
    check(responses, {
        'Discord login loaded': (r) => JSON.stringify(r).includes('Continue'),
    });

    sleep(1);
}
