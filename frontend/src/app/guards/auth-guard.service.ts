import { Injectable } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';




import { ApiService } from '../services/api.service';


@Injectable()
export class AuthGuardService implements CanActivate {

  constructor(private api: ApiService, private router: Router) {}

  canActivate(state: ActivatedRouteSnapshot) {
    const url = state.firstChild.url.join('/');
    console.log(`AuthGuard#canActivate called from ${url}`);
    return this.api.getUserData().
      pipe(
        map((e) => {
          if (e) { return true; }
        }),
        catchError((err) => {
          this.router.navigate(['/login'], {queryParams: {from: url}});
          return of(false);
        })
      );
  }

}
