import { Injectable, TemplateRef, HostListener } from '@angular/core';
import { Router, CanDeactivate } from '@angular/router';
import { Observable } from 'rxjs';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ModalComponent } from '../components/widgets';

export interface ComponentCanDeactivate {
  canDeactivate: () => boolean | Observable<boolean> ;
  modal: NgbModal;
}

@Injectable()
export class PendingChangesGuardService implements CanDeactivate<ComponentCanDeactivate> {

  constructor() { }

  canDeactivate(component: ComponentCanDeactivate): boolean | Promise<boolean> {
    if (!component.canDeactivate()) {
      // NOTE: this warning message will only be shown when navigating elsewhere within your angular app;
      // when navigating away from your angular app, the browser will show a generic warning message
      // see http://stackoverflow.com/a/42207299/7307355`
      const c = component.modal.open(ModalComponent);
      c.componentInstance.confirmText = 'Leave';
      c.componentInstance.cancelText = 'Stay';
      c.componentInstance.dialog = 'You have unsaved changes. Are you sure you want to leave?';
      return c.result.then(() => {
        return true;
      }, () => {
        return false;
      });
    } else {
      return true;
    }

  }
}
