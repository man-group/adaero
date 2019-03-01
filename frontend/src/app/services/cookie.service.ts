import { Injectable } from '@angular/core';

@Injectable()
export class CookieService {

  constructor() { }

  getCookie(name: string) {
    const cookies: Array<string> = document.cookie.split(';');
    const cookieName = `${name}=`;
    let c: string;

    for (const cookie of cookies) {
        c = cookie.replace(/^\s+/g, '');
        if (c.indexOf(cookieName) === 0) {
            return c.substring(cookieName.length, c.length);
        }
    }
    return '';
  }

  deleteCookie(name) {
      this.setCookie(name, '', -1);
  }

  // number = 60 * 60 * 24 * 28
  setCookie(name: string, value: string, maxAgeSeconds: number = 2419200, path: string = '') {
      let maxAge = '';
      if (maxAgeSeconds) {
        maxAge = `max-age=${maxAgeSeconds}`;
      }
      const cpath = path ? `; path=${path}` : '';
      document.cookie = `${name}=${value}; ${maxAge}${cpath}`;
  }
}
