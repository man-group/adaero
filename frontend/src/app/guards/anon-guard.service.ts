import { Injectable } from '@angular/core';
import { Router, CanActivate } from '@angular/router';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';




import { ApiService } from '../services/api.service';


@Injectable()
export class AnonGuardService implements CanActivate {

  constructor(private api: ApiService, private router: Router) {}

  canActivate() {
    console.log('AnonGuard#canActivate called');
    return this.api.getUserData().
      pipe(
        map((e) => {
          if (e) {
            this.router.navigate(['/self-nominate']);
            return false;
          }
        }),
        catchError((err) => {
          return of(true);
        })
      );
  }
}
